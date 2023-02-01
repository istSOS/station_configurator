from ..drivers.trilux import Trilux
import statistics

try:
    s = Trilux("/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTL7EQUO-if00-port0")
    s.start()
    data = s.get_values()
    print(data)
    filtered_data=[]
    p1 = []
    p2 = []
    p3 = []
    for i in range(len(data)):
        if data[i][0]>=0:
            p1.append(data[i][0])
        if data[i][1]>=0:
            p2.append(data[i][1])
        if data[i][2]>=0:
            p3.append(data[i][2])
    values = [-999.99, -999.99, -999.99]
    status = [-100, -100, -100]
    if len(p1) > 0:
        values[0] = round(statistics.mean(p1), 2)
        status[0] = 100
    if len(p2) > 0:
        values[1] = round(statistics.mean(p2), 2)
        status[1] = 100
    if len(p3) > 0:
        values[2] = round(statistics.mean(p3), 2)
        status[2] = 100
    if data:
        s.stop()
    print("OK")
except:
    print("Error")
    values = [-999.99, -999.99, -999.99]
    status = [-100, -100, -100]
    if data:
        s.stop()
    print("Can\'t find sensor")


print("Data: {}".format(values))
print("Status: {}".format(status))
