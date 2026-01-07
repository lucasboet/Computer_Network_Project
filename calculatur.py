
# mini_calculator.py

x = int(input("Enter the first number: "))
y = int(input("Enter the second number: "))
symbol = input("Enter operator (* / + -): ")

if symbol == "*":
    print(x * y)
elif symbol == "/":
    print(x / y)
elif symbol == "+":
    print(x + y)
elif symbol == "-":
    print(x - y)
else:
    print("Invalid operator")
