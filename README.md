# 电机 CAN 16 位寄存器读取脚本

按你最新给的固定协议实现，不需要再设置这些 ID 参数。

## 固定协议（已内置）

- 发送 CAN ID：`0x100 + 电机ID`
  - 例如电机 `11 (0x0B)` -> 发送 ID `0x10B`
- 发送数据（4字节）：`00 0A 01 <addr_low>`
- 接收 CAN ID：固定 `0x700`
- 接收数据（6字节）：`<motor_id> 0C 01 <addr_low> <value_hi> <value_lo>`
  - 寄存器值解析：`value = (value_hi << 8) | value_lo`

示例：

- 发送：`can0 10B [4] 00 0A 01 70`
- 接收：`can0 700 [6] 0B 0C 01 70 00 02`
- 值：`0x0002`（十进制 2）

---

## JSON 格式

`motor_ids.json`：

```json
{"id":[11,12]}
```

`register_addrs.json`：

```json
{"addr":["0x170","0x171"]}
```

---

## 使用方式

### 1) 仅打印将发送的报文（不访问 CAN）

```bash
python3 read_motor_registers.py --ids motor_ids.json --addrs register_addrs.json
```

### 2) 真实读取 CAN

```bash
python3 read_motor_registers.py \
  --ids motor_ids.json \
  --addrs register_addrs.json \
  --read \
  --channel can0 \
  --bustype socketcan \
  --bitrate 500000 \
  --timeout 0.2
```

> 只有通道/波特率/超时可配，协议 ID 与命令字节已固定。

---

## 依赖

真实读取模式需要：

```bash
pip install python-can
```
