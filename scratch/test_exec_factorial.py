import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
import executor

code = """
n = int(input("Enter n: "))
fact = 1
i = 1
while i <= n:
    fact = fact * i
    i = i + 1
print(fact)
""".strip()

res5 = executor.execute(code, "5\n", client_is_local=True)
print("Input 5 Output:", repr(res5.stdout), "Success:", res5.success)
assert "120" in res5.stdout

res0 = executor.execute(code, "0\n", client_is_local=True)
print("Input 0 Output:", repr(res0.stdout), "Success:", res0.success)
assert "1" in res0.stdout
print("ALL EXECUTIONS PASSED!")
