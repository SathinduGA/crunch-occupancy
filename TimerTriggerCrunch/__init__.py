import os
import re
import logging
import requests
import pymongo
from datetime import datetime
from pytz import timezone
from bs4 import BeautifulSoup
import azure.functions as func


logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


def get_page_content():
    try:
        url = f"https://www.crunch.com/locations/{os.environ['APP_LOCATION']}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            logging.error(f"Get Page Error: {response.status_code}")
    except Exception as error:
        logging.error(error)
    return None


def save_data_to_mongo(data):
    try:
        mongo_user = os.environ['MONGO_USER']
        mongo_password = os.environ['MONGO_PASSWORD']
        connection_string = f"mongodb+srv://{mongo_user}:{mongo_password}@cluster0.ksa0nt2.mongodb.net/?retryWrites=true&w=majority"
        client = pymongo.MongoClient(connection_string)
        db = client["crunch"]
        collection = db["occupancy"]
        response = collection.insert_one(data)
        return response
    except Exception as error:
        logging.error(error)
    return None


def main(crunchtimer: func.TimerRequest) -> None:
    try:
        content = get_page_content()
        if content:
            soup = BeautifulSoup(content, "html.parser")
            occupancy_info = soup.find(id="occupancy-info")
            occupancy_bar = occupancy_info.find("div", class_="progress-bar")
            occupancy_value = int(re.search("(?<=width: )(.*)(?=%)", occupancy_bar['style']).group())
            occupancy_status = occupancy_info.find("p", class_="ocupancy-status").text.upper()
            del occupancy_bar, occupancy_info, soup, content
            tz = timezone(os.environ['APP_TIMEZONE'])
            timestamp = datetime.now(tz)
            data = {
                "timestamp": timestamp,
                "occupancy_value": occupancy_value,
                "occupancy_status": occupancy_status,
                "year": timestamp.year,
                "month": timestamp.strftime('%B'),
                "day": timestamp.day,
                "weekday": timestamp.strftime('%A'),
                "hour": timestamp.hour,
                "minute": timestamp.minute,
            }
            mongo_response = save_data_to_mongo(data)
            if mongo_response:
                logging.info(f"Record Inserted at: {timestamp} - Occupancy: {occupancy_value}")
            else:
                logging.error(f"Record Insert Fail at: {timestamp}")
    except Exception as error:
        logging.error(error)
