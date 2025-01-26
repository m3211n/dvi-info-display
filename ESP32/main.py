from machine import UART, Pin
import urequests
import json
import time
import gc

# Configure UART
uart = UART(2, baudrate=115200, tx=Pin(14), rx=Pin(12))  # Ensure TX white and RX green pins are correct
working_pin = Pin(23, Pin.OUT)
waiting_pin = Pin(22, Pin.OUT)

working_pin.value(0)
waiting_pin.value(0)

REFRESH_TIMEOUT = 30
SL_FORECAST = 60 
SL_API_ENDPOINT = "https://transport.integration.sl.se/v1/sites/"
SITE = ("9702", "5875")


def get_weather():
    weather_url = "http://api.weatherapi.com/v1/current.json?key=3ea5aa9d2d974bff9c0183926241711&q=Stockholm&aqi=no"
    try:
        weather_r = urequests.get(weather_url).json()
    except:
        return ("--", "--", "--", "--")
    print("Weather: OK")
    return (
        str(round(weather_r['current']['temp_c'])),
        str(round(weather_r['current']['precip_mm'])),
        str(round(weather_r['current']['wind_kph'] * 0.277778)),
        str(round(weather_r['current']['cloud']))
    )


def get_time():
    print("Getting time...")
    try:
        time_r = urequests.get("https://www.timeapi.io/api/time/current/zone?timeZone=Europe%2FStockholm").json()
    except:
        return "--:--"
    time_str = str(time_r['time'])
    print(f"Time: {time_str}")
    return time_str
    
    
def get_sl_schedule(transport, forecast, stop_point_id):
    sl_data = []
    index = 0
    if transport == "TRAIN":
        site = SITE[0]
    elif transport == "BUS":
        site = SITE[1]
    else:
        return None
    url = f"{SL_API_ENDPOINT}{site}/departures?transport={transport}&forecast={forecast}"
    print(f"{transport} data URL:{url}")
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            json_data = response.json()
            sl_data.append(forecast) # forecast scope
            for departure in json_data['departures']:
                if departure['stop_point']['id'] == stop_point_id and departure['state'] == "EXPECTED":
                    index_last = index # Index of the last departure in the list with needed stop_point_id
                    sl_data.append(departure['display'])
                index += 1

            # SL API does not provide the same type of data in 'direction' field in JSON.
            # For BUS it could be 2 or even 3 names in one. In such case, this condition
            # takes the destination instead
            
            dir = json_data['departures'][index_last]['direction']
            if transport == "BUS":
                dir = json_data['departures'][index_last]['destination']

            sl_data.insert(0, f"{json_data['departures'][index_last]['stop_point']['name']} \u007f {dir}")     # direction name
            print(f"{transport} schedule: OK")
    except Exception as e:
        return e
    return sl_data


def get_send_data():
    """
    Function to get data from APIs, create a JSON object for the recipient
    
    and to send data over UART.
    """
    data = {}
    print("Fetching data...")
    working_pin.value(1)
    data = {
        "T"  : get_time(),
        "W"  : get_weather(),
        "TR1": get_sl_schedule("TRAIN", SL_FORECAST, 6061),
        "TR2": get_sl_schedule("TRAIN", SL_FORECAST, 6062),
        # "B2" : get_sl_schedule("BUS", SL_FORECAST / 2, 51583),
        "FC" : SL_FORECAST,
        "TO" : REFRESH_TIMEOUT
    }
    data = json.dumps(data)
    print(f">> {data}")
    print("Sending data...")
    # Sending data to UART
    uart.write(data + '\n') # Append newline for easier parsing
    print(f"Transmission complete. Sleeping for {REFRESH_TIMEOUT} sec.")
    working_pin.value(0)
    time.sleep(REFRESH_TIMEOUT) # Wait before sending the next batch
    gc.collect()
    pass


def recipient_ready(timeout):
    start_time = time.ticks_ms()  # Get the current time
    print("Waiting for recepient to respond...")
    while (time.ticks_ms() - start_time) < timeout:
        response = uart.readline()
        if response == b"++\n":
            print("RP2040 is ready!")
            return True
        waiting_pin.value(1)
        time.sleep(0.1)  # Add a short delay to avoid busy-waiting
        waiting_pin.value(0)
    return False


# Continuous send and wait for confirmation
while True:
    if recipient_ready(REFRESH_TIMEOUT * 1000):
        waiting_pin.value(0)
        get_send_data()
    else:
        print(f"RP2040 was not ready. Trying again...")

