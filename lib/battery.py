from ina219 import INA219, DeviceRangeError
from time import sleep


def to_255(v):
  if v <= 10.5:
    return 1
  elif v <= 11.31:
    return 25
  elif v <= 11.58:
    return 51
  elif v <= 11.75:
    return 77
  elif v <= 11.9:
    return 102
  elif v <= 12.06:
    return 128
  elif v <= 12.2:
    return 153
  elif v <= 12.32:
    return 179
  elif v <= 12.42:
    return 204
  elif v <= 12.5:
    return 230
  elif v <= 12.7:
    return 242
  else:
    return 254

def read_ina219():
    try:
        SHUNT_OHMS = 0.1
        MAX_EXPECTED_AMPS = 2.0
        ADDRESS=0x40
<<<<<<< HEAD
        #ina = INA219(
        #  shunt_ohms=SHUNT_OHMS,
        #  address=ADDRESS
        #)
        #ina.configure(ina.RANGE_16V)
        ina = INA219(
            SHUNT_OHMS, 1.6, address=ADDRESS
        )
        ina.configure(ina.RANGE_32V, ina.GAIN_8_320MV)
=======
        ina = INA219(
          shunt_ohms=SHUNT_OHMS,
          address=ADDRESS
        )
        ina.configure(ina.RANGE_16V)
>>>>>>> f458bed988a6ec7c473e3481d28ad42ee02c6129
        # ina.configure()
        print('Bus Voltage: {0:0.2f}V'.format(ina.voltage()))
        print('Bus Current: {0:0.2f}mA'.format(ina.current()))
        print('Power: {0:0.2f}mW'.format(ina.power()))
        print('Shunt Voltage: {0:0.2f}mV\n'.format(ina.shunt_voltage()))
        return to_255(ina.voltage())
    except DeviceRangeError as e:
        # Current out of device range with specified shunt resister
        print("DeviceRangeError")
        return 254
    except:
        print("Errors found or no INA219 detected")
        return 254
