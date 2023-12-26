import firebase_admin
from firebase_admin import credentials, db
from model import User, Test, Task


cred = credentials.Certificate("???")
firebase_admin.initialize_app(cred, {
    'databaseURL': '???'
})
ref = db.reference('/')
tasks_ref = ref.child('tasks')
users_ref = ref.child('users')


def get_tasks():
    tasks = []
    tasks_data = tasks_ref.get()
    if tasks_data:
        for task_key, task_data in tasks_data.items():
            task = Task(name=task_data['name'], description=task_data['description'],
                        example=task_data['example'], func_name=task_data['func_name'],
                        variables=task_data['variables'], solution=task_data['solution'])
            tests = []
            if task_data.get('tests'):
                for test_key, test_data in task_data['tests'].items():
                    test = Test(test_data['lines'], test_data['answer'])
                    tests.append(test)
                task.tests = tests
            tasks.append(task)
    else:
        print("No tasks in DataBase")
    return tasks


def add_user(user):
    in_database = False
    users_data = users_ref.get()
    if users_data:
        for user_key, user_data in users_data.items():
            if user_data['id'] == user.id:
                in_database = True
                if user_data['username'] != user.username:
                    users_ref.child(user_key).update({'username': user.username})
                break
    if not in_database:
        users_ref.child(str(user.id)).set({
            'id': user.id,
            'username': user.username,
            'status': user.status,
        })


def add_task(task):
    task_ref = tasks_ref.child(f"task_{task.name}")
    task_ref.set({
        'description': task.description,
        'example': task.example,
        'name': task.name,
        'func_name': task.func_name,
        'variables': task.variables,
        'solution': task.solution
    })

    for index, test in enumerate(task.tests):
        test_ref = task_ref.child('tests').child(f"test{index}")
        test_ref.set({
            'lines': test.lines,
            'answer': test.answer
        })


def set_user_status_by_id(user_id, new_status):
    users_data = users_ref.get()
    if users_data:
        for user_key, user_data in users_data.items():
            if user_data['id'] == user_id:
                users_ref.child(user_key).update({'status': new_status})
                return
        print("Error while finding user by id")
    print("No users data")


def get_user_status_by_id(user_id):
    users_data = users_ref.get()
    if users_data:
        for user_key, user_data in users_data.items():
            if user_data['id'] == user_id:
                return user_data.get('status')
    return None


def update_task_func_name(task_name, new_func_name):
    task_ref = tasks_ref.child(task_name)
    task_ref.update({'func_name': new_func_name})


def update_task_example(task_name, new_example):
    task_ref = tasks_ref.child(task_name)
    task_ref.update({'example': new_example})


def update_task_description(task_name, new_description):
    task_ref = tasks_ref.child(task_name)
    task_ref.update({'description': new_description})


def update_task_solution(task_name, new_solution):
    task_ref = tasks_ref.child(task_name)
    task_ref.update({'solution': new_solution})


def update_task_variables(task_name, new_variables):
    task_ref = tasks_ref.child(task_name)
    task_ref.update({'variables': new_variables})


def add_test_to_task(task_name, test):
    task_ref = tasks_ref.child(task_name)
    tests_ref = task_ref.child('tests')
    existing_tests = tests_ref.get()
    test_index = 0 if existing_tests is None else len(existing_tests)
    test_ref = tests_ref.child(f"test{test_index}")
    test_ref.set({
        'lines': test.lines,
        'answer': test.answer
    })


def delete_task(task_name):
    task_ref = tasks_ref.child(task_name)
    task_ref.child('tests').delete()
    task_ref.delete()


def has_admin_roots(user_id):
    users_data = users_ref.get()
    if users_data:
        for user_key, user_data in users_data.items():
            if user_data['id'] == user_id:
                roots = users_ref.child(user_key).child("admin_roots")
                if roots.get() is None:
                    return False
                return roots.get()
    return False


def give_admin_roots(user_id):
    users_data = users_ref.get()
    if users_data:
        for user_key, user_data in users_data.items():
            if user_data['id'] == int(user_id):
                users_ref.child(user_key).child("admin_roots").set(True)
