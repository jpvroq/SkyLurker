# ADS-B Exchange API Example
import requests

url = "https://www.adsbexchange.com/api/data/aircraft/A27D05"
headers = {
    "Content-Type": "application/json"
}

response = requests.get(url)
data = response.text.splitlines()
print(data)
