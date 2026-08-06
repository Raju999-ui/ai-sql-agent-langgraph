from langgraph_agent import build_langgraph_agent, run_agent
import logging

# Enable logging to see what query is generated
logging.basicConfig(level=logging.INFO)

agent = build_langgraph_agent()

print("--- Query 1: Show 5 movies from 2020 ---")
state1 = {
    "user_input": "Show 5 movies from 2020",
    "schema_context": "",
    "sql": "",
    "result": [],
    "error": "",
    "previous_error": "",
    "db_type": "sqlite"
}
res1 = agent.invoke(state1)
print("Query 1 result keys:", res1.keys())
print("Query 1 SQL:", res1.get("sql"))
print("Query 1 Error:", res1.get("error"))
print("Query 1 Result:", res1.get("result"))

print("\n--- Query 2: only from USA ---")
state2 = {
    "user_input": "only from USA",
    "schema_context": "",
    "sql": "",
    "result": [],
    "error": "",
    "previous_error": "",
    "db_type": "sqlite"
}
try:
    res2 = agent.invoke(state2)
    print("Query 2 SQL:", res2.get("sql"))
    print("Query 2 Error:", res2.get("error"))
    print("Query 2 Result:", res2.get("result"))
except Exception as e:
    import traceback
    traceback.print_exc()
