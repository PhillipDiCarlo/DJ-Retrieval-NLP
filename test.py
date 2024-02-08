import discord
import requests
import logging
from dotenv import load_dotenv
import os
from fuzzywuzzy import process
# from openai import OpenAI
import json
import re


# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Load environment variables
load_dotenv()

# Discord client setup
intents = discord.Intents.default()
intents.messages = True  # Enables receiving messages
discordClient = discord.Client(intents=intents)

# # OpenAI Client Setup
# openaiClient = OpenAI(
#     api_key=os.environ.get("CHATGPT_API_KEY")
# )

# Function to retrieve and parse the JSON file
def get_dj_data():
    response = requests.get('https://raw.githubusercontent.com/PhillipDiCarlo/ClubLAAssets/main/CLA_DJ_Links.json')
    if response.status_code == 200:
        global dj_vj_json
        dj_vj_json = response.json()  # Save the entire JSON
        # Extracting DJ and VJ names
        dj_names = [dj['DJ_Name'] for dj in dj_vj_json.get('DJs', [])]
        vj_names = [vj['VJ_Name'] for vj in dj_vj_json.get('VJs', [])]
        all_names = dj_names + vj_names  # Combine DJ and VJ names
        # Create CSV string
        dj_vj_csv = ','.join(all_names)
        # print("XYZ" + dj_vj_csv)

        return dj_vj_csv
    else:
        return None

# Function to determine request type (Quest or Non-Quest)
def determine_request_type(message):
    # quest_keywords = ['quest', 'quest friendly', 'quest compatible']
    non_quest_keywords = ['non quest', 'non-quest', 'no quest', 'non quest friendly', 'non-quest compatible']

    if any(keyword in message.lower() for keyword in non_quest_keywords):
        return "non-quest"
    return "quest"

def get_chatgpt_response(dj_data, user_message):
    
    # Format the data for ChatGPT
    cleaned_text = re.sub(r"<@.*?>", "", user_message)
    pattern = r"(non[-\s]?quest\s+links?\s+for|quest\s+links?\s+for|non[-\s]?quest\s+links?|quest\s+links?|non[-\s]?quest\s+for|quest\s+for)"
    cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE).strip()

    requested_names = [name.strip() for name in cleaned_text.split(',')]
    dj_name_list = [name.strip() for name in dj_data.split(',')]

    finalMatchedNames = {}
    for name in requested_names:
        best_match = process.extractOne(name, dj_name_list)
        finalMatchedNames[name] = best_match[0]
    
    return finalMatchedNames


    # completion = openaiClient.chat.completions.create(
    # model="gpt-3.5-turbo-1106",
    # messages=[
    #     {"role": "system", "content": "You are an automated program designed to return a list of names (in CSV format) based from the given list of DJ/VJ names. You will return only a match of the given names in the same order as mentioned. Please note the names may be given mistyped."},
    #     {"role": "user", "content": f"Match the following names: {cleaned_text} . To the list here: {dj_data}."} 
    # ]
    # )
    # return completion.choices[0].message.content

def parse_csv_and_fetch_links(matched_names, request_type):
    requestedLinks = []
    link_type = "Quest_Friendly" if request_type == 'quest' else "Non-Quest_Friendly"

    # Loop through matched_names values
    for original_name, matched_name in matched_names.items():
        nameFound = False
        for category in ['DJs', 'VJs']:
            if nameFound:
                break
            for item in dj_vj_json.get(category, []):
                if item.get('DJ_Name') == matched_name:  # Use matched_name
                    link = item.get(link_type)
                    requestedLinks.append(f"{matched_name} - {link}")
                    nameFound = True
                    break
    
    # Check if no names were found and handle accordingly
    if not requestedLinks:
        return ["No links found for the requested names."]
    
    return requestedLinks


# Bot event handling
@discordClient.event
async def on_ready():
    logging.info(f'Logged in as {discordClient.user}')
    global dj_data
    try:
        dj_data = get_dj_data()
        if dj_data is None:
            logging.error('Failed to fetch or parse DJ data')
    except Exception as e:
        logging.error(f'Error during data fetching: {e}')

@discordClient.event
async def on_message(message):
    try:
        if discordClient.user.mentioned_in(message) and message.mentions:
            message_content = message.content
            request_type = determine_request_type(message_content)

            csv_response = get_chatgpt_response(dj_data, message_content)
            if csv_response:
                links_response = parse_csv_and_fetch_links(csv_response, request_type)
                response_message = "\n".join(links_response)
                await message.channel.send(response_message)
            else:
                logging.warning('No response from ChatGPT or response parsing failed')
    except Exception as e:
        logging.error(f'Error handling message: {e}')

discordClient.run(os.getenv('DISCORD_BOT_TOKEN'))