from langgraph_agent import run_agent
import json

def test():
    print("Testing agent with a basic movie query in SQLite mode...")
    try:
        res = run_agent("Show 5 movies from 2020", db_type="sqlite")
        print("\nAgent Response:")
        print("SQL:", res.get("sql"))
        print("Error:", res.get("error"))
        print("Result length:", len(res.get("result", [])))
        print("Result samples:")
        for r in res.get("result", [])[:5]:
            print("  ", r)
            
        print("\nTesting context/memory - follow up query:")
        res2 = run_agent("only from USA", db_type="sqlite")
        print("SQL:", res2.get("sql"))
        print("Error:", res2.get("error"))
        print("Result length:", len(res2.get("result", [])))
        for r in res2.get("result", [])[:5]:
            print("  ", r)
            
    except Exception as e:
        print("Error running agent:", e)

if __name__ == "__main__":
    test()
