class User:
    def __init__(self, id, username="", status=""):
        self.id = id
        self.username = username
        if username is None:
            self.username = ""
        self.status = status

    def set_status(self, status):
        self.status = status


class Test:
    def __init__(self, lines, answer):
        self.lines = lines
        self.answer = answer

    def to_input(self):
        result = ""
        for line in self.lines:
            if result != "":
                result += ", "
            result += line
        return result

    def check_test(self, result):
        result = result.split("\n")
        result = result[:-1] if result[-1] == '' else result
        return self.answer == result


class Task:
    def __init__(self, name, description="No description yet", example="", tests=[], func_name="",
                 solution="No solution", variables=""):
        self.name = name
        self.func_name = func_name
        self.description = description
        self.example = example
        self.solution = solution
        self.variables = variables
        self.tests = tests

    def add_description(self, description):
        self.description = description

    def add_test(self, test):
        self.tests.append(test)
