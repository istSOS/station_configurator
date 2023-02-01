#!/usr/bin/env python
#
#   Copyright 2014 CNR-ISE
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
  # Fissa indirizzo sullo strumento
  # instrument.address=0
  # instrument.write_register(0xa3,11,0,6)

  Modbus for raspberry
    sudo apt-get install python-pip
    pip install -U minimalmodbus
    https://pypi.python.org/pypi/MinimalModbus/1.0.2
"""

import minimalmodbus
import serial
import sys
import time
import argparse

__author__ = "Stefano Grisoni - Dario Manca"
__email__ = "grisoni.stefano@gmail.com - manca.dario@gmail.com"
__license__ = "Apache License, Version 2.0"

__revision__ = "$Rev: 100 $"
__date__ = "$Date: 2014-12-28 20:58:30 $"


class Ponsel(minimalmodbus.Instrument):
    """Instrument class for Ponsel sensor

    Communicates via Modbus RTU protocol (via RS232 or RS485),
    using the *MinimalModbus* Python module.
    Args:
        * portname (str): port name
        * slaveaddress (int): slave address in the range 1 to 247

    Implemented with these function codes (in decimal):

    ==================  ====================
    Description         Modbus function code
    ==================  ====================
    Read registers      3
    Write registers     6
    ==================  ====================

    """

    def __init__(self, portname, slaveaddress):
        self.addr = slaveaddress
        self.port = portname
        self.instr = minimalmodbus.Instrument(portname, slaveaddress)
        self.instr.serial.baudrate = 9600
        self.instr.serial.timeout = 0.1
        self.instr.serial.stopbits = 2
        self.instr.serial.flush()

        # register settings
        self.pars_reg = [0x53, 0x55, 0x57, 0x59, 0x5b]
        self.pars_status_reg = [0x64, 0x65, 0x66, 0x67, 0x68]
        self.pars_unit_reg = [0x0d22, 0x0d25, 0x0d28, 0x0d2b, 0x0d2e]

    def __ctrl_read_register(self, reg, dec):
        retray = 2
        while (retray > 0):
            self.instr.serial.flushInput()
            try:
                return self.instr.read_register(reg, dec)
            except Exception as e:
                retray = retray-1
        return 0x00

    def __ctrl_write_register(self, reg, val, dec, funz):
        self.instr.serial.flushInput()
        try:
            return self.instr.write_register(reg, val, dec, funz)
        except Exception as e:
            return 0

    def __ctrl_read_string(self, reg, ncar):
        self.instr.serial.flushInput()
        try:
            return self.instr.read_string(reg, ncar)
        except Exception as e:
            return 0

    def __ctrl_read_float(self, reg, mod):
        self.instr.serial.flushInput()
        try:
            return self.instr.read_float(reg, mod)
        except Exception as e:
            return 0.0

    def get_gen_status(self):
        """
        StmTemp:Stm4:Stm3:Stm2:Stm1:StmT:
        StmX:	000: Measurement OK
                001: Measurement OK, but out of specifications
                010: Measurement OK with INFO 1
                011: Measurement OK with INFO 2
                100: Measurement impossible, out of specifications
                101: Measurement impossible with INFO 3
                110: Measurement impossible with INFO 4
                111: measurement under way (not yet available)
        StmTemp	  1: if at least one coefficient uses
                     a temporary calibration standard
                     (configuration during calibration)
        """

        return self.__ctrl_read_register(0x52, 0)

    def get_par_status(self, reg):
        """
        StmGamme:StmME:StmHIST:StmCU:StmHF:StmTemp:Stm
        Stm:		See StmX
        StmTemp: 	1: if at least one parameter coefficient uses
                       a temporary calibration standard
                       (configuration during calibration)
        StmHF: 		1: if at least one parameter coefficient is
                       outside calibration limits
        StmCU: 		1: if all parameter coefficients use default coefficient
        StmHIST: 	1: if all parameter coefficients use history coefficient
        StmME: 		1: if dry weight is missing in at least one
                       parameter coefficient (measurement under way)
        StmGamme:	001: measurement used range 1
                    010: measurement used range 2
                    011: measurement used range 3
                    100: measurement used range 4
        """
        return self.__ctrl_read_register(reg, 0)

    def set_address(self, addr):
        """
        M4	M3	M2	M1	MT

        MT: 1: runs temperature measurement
        M1: 1: runs parameter 1 measurement
        M2: 1: runs parameter 2 measurement
        M3: 1: runs parameter 3 measurement
        M4: 1: runs parameter 4 measurement
        """

        return self.__ctrl_write_register(0x00A3, addr, 0, 6)

    def set_run_measurement(self, runs):
        """
        M4	M3	M2	M1	MT

        MT: 1: runs temperature measurement
        M1: 1: runs parameter 1 measurement
        M2: 1: runs parameter 2 measurement
        M3: 1: runs parameter 3 measurement
        M4: 1: runs parameter 4 measurement
        """

        return self.__ctrl_write_register(0x01, runs, 0, 6)

    def get_par(self, reg):
        return self.__ctrl_read_float(reg, 3)

    def get_par_unit(self, reg):
        return self.__ctrl_read_string(reg, 3)

    def get_pod_desc(self):
        return self.__ctrl_read_string(0x0d00, 16)

    def get_serial_number(self):
        return self.__ctrl_read_string(0x0d10, 16)

    def get_sw_version(self):
        # Heavy Weight: Major version and Light Weight:
        # Minor Version.
        return self.__ctrl_read_register(0x0d20, 0)

    def get_hw_version(self):
        # Heavy Weight: Major version and Light Weight:
        # Minor Version.
        return self.__ctrl_read_register(0x0d21, 0)

    def get_time_of_measure(self):
        return self.__ctrl_read_register(0xa4, 0)

    def get_values(self):
        return list(
            map(
                lambda x: self.get_par(x), self.pars_reg
            )
        )

    def get_status(self):
        return list(
            map(
                lambda x: self.get_par_status(x), self.pars_status_reg
            )
        )

    def show_info(self):
        print(serial.Serial(self.port).is_open)
        minimalmodbus._print_out(' ')
        minimalmodbus._print_out('Address:                {0}'.format(
            self.addr
        ))
        minimalmodbus._print_out('Baudrate:               {0}'.format(
            self.instr.serial.baudrate
        ))
        minimalmodbus._print_out('ComPort:                {0}'.format(
            self.port
        ))
        minimalmodbus._print_out('...........................')
        minimalmodbus._print_out('TimeOfMeasure:          {0} ms'.format(
            self.get_time_of_measure()
        ))
        minimalmodbus._print_out('Status Generic:         {0}'.format(
            hex(self.get_gen_status())
        ))
        for i in range(len(self.pars_status_reg)):
            minimalmodbus._print_out('Status Par{0}:            {1}'.format(
                i+1,
                hex(self.get_par_status(self.pars_status_reg[i]))
            ))
            minimalmodbus._print_out('Par{0}:                   {1}'.format(
                i+1,
                self.get_par(self.pars_reg[i])
            ))
            minimalmodbus._print_out('Par unit{0}:              {1}'.format(
                i+1,
                self.get_par_unit(self.pars_unit_reg[i])
            ))
        minimalmodbus._print_out('POD:                    {0}'.format(
            self.get_pod_desc()
        ))
        minimalmodbus._print_out('Serial number:          {0}'.format(
            self.get_serial_number()
        ))
        minimalmodbus._print_out('Sw Version :            {0}'.format(
            self.get_sw_version()
        ))
        minimalmodbus._print_out('Hw Version :            {0}'.format(
            self.get_hw_version()
        ))


def execute(args):
    minimalmodbus._print_out('----------------------------')
    minimalmodbus._print_out('TESTING PONSEL MODBUS MODULE')
    minimalmodbus._print_out('----------------------------')

    a = Ponsel(
        args['ser'],
        int(args['addr'])
    )
    a.instr.debug = args['d']

    a.set_run_measurement(0x001f)
    time.sleep(1)
    a.show_info()

    minimalmodbus._print_out('---------------------------')


########################
#  Testing the module  #
########################


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Export data in CSV format'
    )

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        dest='d',
        help='Activate/deactivate debug (bool)'
    )
    parser.add_argument(
        '-s', '--serial',
        action='store',
        dest='ser',
        default='/dev/ttyUSB0',
        help=(
            'System serial port (str)'
        )
    )
    parser.add_argument(
        '-a', '--address',
        action='store',
        dest='addr',
        help=(
            'Modbus sensor address (int)'
        )
    )
    args = parser.parse_args()
    execute(args.__dict__)


#     ser = '/dev/ttyUSB0'
#     addr = 11
#     dbgEnable = False

#     print(sys.argv)

#     num = len(sys.argv)
#     if num > 1:
#         for i in range(1, num):
#             if sys.argv[i] == "-h" or sys.argv[i] == "?":  # debug mode
#                 print('sudo python ponsel1.py [par]')
#                 print('par:')
#                 print('-c = calibration')
#                 print('-d = verbose for debug')
#                 print('-s = serial Ex. -s /dev/ttyUSB0')
#                 print('-a = instrument address Ex. -a 10')
#                 quit()
#             if sys.argv[i] == "-d":  # debug mode
#                 dbgEnable = True
#             if sys.argv[i] == "-a":  # address
#                 addr = int(sys.argv[i+1])
#             if sys.argv[i] == "-s":  # serial
#                 ser = sys.argv[i+1]

#     minimalmodbus._print_out('----------------------------')
#     minimalmodbus._print_out('TESTING PONSEL MODBUS MODULE')
#     minimalmodbus._print_out('----------------------------')

#     a = Ponsel(ser, addr)
#     a.instr.debug = dbgEnable

#     a.set_run_measurement(0x001f)
#     time.sleep(1)
#     a.show_info()

#     minimalmodbus._print_out('---------------------------')
# pass

#     def set_debug(self):
#         self.instr.debug = True

#     def is_sprate_disabled_loop1(self):
#         return __ctrl_self.read_register(78, 1) > 0

#     def disable_sprate_loop1(self):
#         VALUE = 1
#         self.__ctrl_write_register(78, VALUE, 0)

#     def is_inhibited_loop1(self):
#         return self.__ctrl_read_register(268, 1) > 0

#     def get_op_loop2(self):
#         return self.__ctrl_read_register(1109, 1)

#    def get_threshold_alarm1(self):
#         return self.__ctrl_read_register(10241, 1)
