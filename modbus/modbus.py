# test_modbus.py
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('localhost', port=20001)
client.connect()

result = client.read_holding_registers(0, count=6, slave=1)
if not result.isError():
    regs = result.registers
    print(f"车辆状态:    {regs[0]}")
    print(f"传送线动作:  {regs[1]}")
    print(f"X坐标(cm):   {regs[2] - 30000}")
    print(f"Y坐标(cm):   {regs[3] - 30000}")
    print(f"角度:        {(regs[4] / 10 - 180)} deg")
    print(f"任务状态:    {regs[5]}")
else:
    print("读取失败:", result)

client.close()
