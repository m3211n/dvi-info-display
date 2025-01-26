# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

def do_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WIFI...')
        wlan.connect('Home Sweet Home', '82840813.home')
        while not wlan.isconnected():
            pass
    print('Connected to WIFI. IP:', wlan.ifconfig()[0])

do_connect()
