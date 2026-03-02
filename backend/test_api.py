import requests

url = "http://localhost:8000/api/evaluate"
files = {
    'teacherKey': ('test.txt', open('e:/incubation/Ai-automated-paper-correction/backend/utils.py', 'rb')),
    'studentScript': ('test2.txt', open('e:/incubation/Ai-automated-paper-correction/backend/utils.py', 'rb'))
}
data = {'subject': 'Language'}

try:
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
