import sys
from langgraph_agent import run_agent

def run_query(query: str):
    print(f"\nQuestion: \"{query}\"")
    print("=" * 80)
    res = run_agent(query, db_type="sqlite")
    if res.get("error"):
        print(f"Error: {res.get('error')}")
    else:
        print(f"Generated SQL:\n{res.get('sql')}\n")
        results = res.get("result", [])
        print(f"Results Count: {len(results) if results else 0} records")
        if results:
            print("Samples:")
            for i, row in enumerate(results[:10], 1):
                print(f"  {i}. {row}")
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more records")
    print("=" * 80)

if __name__ == "__main__":
    default_query = "What are the top 5 highest-rated movies with an IMDb score?"
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else default_query
    run_query(query)
