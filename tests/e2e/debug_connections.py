"""PostgreSQLのコネクション状態を確認するデバッグユーティリティ."""

# flake8: noqa

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.utils.database import get_database_url


async def check_connections():
    """PostgreSQLのアクティブな接続とロック状態を確認."""
    engine = create_async_engine(get_database_url())
    try:
        async with engine.connect() as conn:
            # アクティブな接続数を確認
            result = await conn.execute(
                text(
                    """
                SELECT
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
                WHERE datname = current_database()
            """
                )
            )
            row = result.fetchone()
            print("\n=== PostgreSQL Connections ===")
            print(
                f"Total: {row[0]}, Active: {row[1]}, Idle: {row[2]}, Idle in Transaction: {row[3]}"
            )

            # ロック待ちを確認
            result = await conn.execute(
                text(
                    """
                SELECT
                    blocked_locks.pid AS blocked_pid,
                    blocked_activity.usename AS blocked_user,
                    blocking_locks.pid AS blocking_pid,
                    blocking_activity.usename AS blocking_user,
                    blocked_activity.query AS blocked_statement,
                    blocking_activity.query AS blocking_statement
                FROM pg_catalog.pg_locks blocked_locks
                JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
                JOIN pg_catalog.pg_locks blocking_locks
                    ON blocking_locks.locktype = blocked_locks.locktype
                    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
                    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
                    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
                    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
                    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
                    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
                    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
                    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
                    AND blocking_locks.pid != blocked_locks.pid
                JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
                WHERE NOT blocked_locks.granted
            """
                )
            )
            locks = result.fetchall()
            if locks:
                print("\n=== Lock Conflicts Found ===")
                for lock in locks:
                    print(f"Blocked PID: {lock[0]}, Blocking PID: {lock[2]}")
                    print(f"  Blocked query: {lock[4][:100]}")
                    print(f"  Blocking query: {lock[5][:100]}")
            else:
                print("\n=== No Lock Conflicts ===")

            # 長時間実行中のクエリ
            result = await conn.execute(
                text(
                    """
                SELECT pid, state, query_start, state_change, query
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND state != 'idle'
                AND query NOT LIKE '%pg_stat_activity%'
                ORDER BY query_start
            """
                )
            )
            long_running = result.fetchall()
            if long_running:
                print("\n=== Active Queries ===")
                for row in long_running:
                    print(f"PID: {row[0]}, State: {row[1]}, Started: {row[2]}")
                    print(f"  Query: {row[4][:100]}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_connections())
