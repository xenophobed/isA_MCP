from neo4j import GraphDatabase

def test_gds_installation():
    # Connection details
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "admin@123"  # Replace with your password

    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Test 1: Check if GDS is installed
            try:
                result = session.run("CALL gds.list()")
                print("✅ GDS is installed and accessible")
                print("\nAvailable procedures:")
                for record in result:
                    print(f"- {record['name']}")
            except Exception as e:
                print("❌ GDS test failed:", e)

            # Test 2: Try a simple GDS operation
            try:
                result = session.run("""
                CALL gds.graph.list()
                YIELD graphName
                RETURN count(graphName) as count
                """)
                count = result.single()["count"]
                print(f"\n✅ GDS can list graphs. Found {count} projected graphs")
            except Exception as e:
                print("\n❌ Cannot list graphs:", e)

    except Exception as e:
        print("❌ Connection failed:", e)
    finally:
        driver.close()

if __name__ == "__main__":
    test_gds_installation()