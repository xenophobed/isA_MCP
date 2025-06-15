import asyncio
import pandas as pd
from app.config.config_manager import config_manager

async def test_duckdb_basic():
    """测试DuckDB基本功能"""
    try:
        # 获取DuckDB服务实例
        db = await config_manager.get_db("duckdb")
        print("✓ 成功获取DuckDB服务实例")

        # 测试创建表
        with db.transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR,
                    value DOUBLE
                )
            """)
        print("✓ 成功创建测试表")

        # 测试插入数据
        test_data = [
            (1, 'test1', 1.1),
            (2, 'test2', 2.2),
            (3, 'test3', 3.3)
        ]
        with db.transaction() as conn:
            for id, name, value in test_data:
                conn.execute(
                    "INSERT INTO test_table (id, name, value) VALUES (?, ?, ?)",
                    [id, name, value]
                )
        print("✓ 成功插入测试数据")

        # 测试查询数据
        df = db.query_df("SELECT * FROM test_table ORDER BY id")
        print("\n查询结果:")
        print(df)
        print("✓ 成功查询数据")

        # 测试参数化查询
        result_df = db.query_df(
            "SELECT * FROM test_table WHERE value > ?",
            params=[2.0]
        )
        print("\n参数化查询结果 (value > 2.0):")
        print(result_df)
        print("✓ 成功执行参数化查询")

        # 测试事务回滚
        try:
            with db.transaction() as conn:
                conn.execute("INSERT INTO test_table VALUES (4, 'test4', 4.4)")
                raise Exception("测试回滚")
        except Exception as e:
            print("✓ 成功测试事务回滚")

        # 验证回滚结果
        df = db.query_df("SELECT * FROM test_table ORDER BY id")
        print("\n回滚后的数据:")
        print(df)

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        raise
    finally:
        # 清理测试表
        with db.transaction() as conn:
            conn.execute("DROP TABLE IF EXISTS test_table")
        print("✓ 成功清理测试表")

async def main():
    print("开始DuckDB服务测试...\n")
    await test_duckdb_basic()
    print("\n所有测试完成!")
    await config_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())