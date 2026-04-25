# 电机 CAN 16 位寄存器读取脚本

这个仓库提供一个 Python 脚本：`read_motor_registers.py`，用于：

1. 从 JSON 文件读取电机 ID 列表。
2. 从 JSON 文件读取寄存器地址列表。
3. 按电机分组打印寄存器列表（默认模式，不需要 CAN 硬件）。
4. 可选：通过 CAN 总线真实读取寄存器值（`--read` 模式）。

---

## 1) 环境要求

- Python 3.8+
- （可选）如果要真实走 CAN：
  - `python-can`
  - 系统有可用 CAN 接口（例如 Linux `socketcan` 的 `can0`）

安装可选依赖：

```bash
pip install python-can
```

---

## 2) JSON 文件格式

### 电机 ID 文件（例如 `motor_ids.json`）

```json
{"id":[1,2,3,4]}
```

### 寄存器地址文件（例如 `register_addrs.json`）

```json
{"addr":["0x170","0x171","0x172"]}
```

> 地址支持十六进制字符串（如 `"0x170"`）或整数。

---

## 3) 如何使用（Shell 示例）

### 示例 A：仅打印“每个电机要读取哪些寄存器”（不访问 CAN）

```bash
python3 read_motor_registers.py \
  --ids motor_ids.json \
  --addrs register_addrs.json
```

示例输出：

```text
电机 ID 1:
  - 寄存器 0x0170
  - 寄存器 0x0171
  - 寄存器 0x0172
电机 ID 2:
  - 寄存器 0x0170
  - 寄存器 0x0171
  - 寄存器 0x0172
...
```

### 示例 B：真实读取 CAN（需要 CAN 环境）

```bash
python3 read_motor_registers.py \
  --ids motor_ids.json \
  --addrs register_addrs.json \
  --read \
  --channel can0 \
  --bustype socketcan \
  --bitrate 500000 \
  --source-id 0x0A \
  --tx-base-id 0x600 \
  --rx-id 0x600 \
  --cmd 0x01 \
  --timeout 0.2
```

---

## 4) 参数说明

- `--ids`：电机 ID JSON 路径（必填）
- `--addrs`：寄存器地址 JSON 路径（必填）
- `--read`：启用真实 CAN 读取（默认不启用）
- `--channel`：CAN 通道，默认 `can0`
- `--bustype`：`python-can` 接口类型，默认 `socketcan`
- `--bitrate`：波特率，默认 `500000`
- `--source-id`：主站 ID，默认 `0x0A`
- `--tx-base-id`：发送 CAN ID 基值，默认 `0x600`（最终发送 ID = 基值 + 电机 ID）
- `--rx-id`：接收应答 CAN ID，默认 `0x600`
- `--cmd`：读取命令字节，默认 `0x01`
- `--timeout`：每个寄存器等待应答超时（秒），默认 `0.2`

---

## 5) 快速自测

```bash
python3 read_motor_registers.py --ids motor_ids.json --addrs register_addrs.json
```

如果你只想先确认 JSON 配置是否正确，先用默认模式（不加 `--read`）即可。


## 6) 协议示例（按你提供的帧）

例如读取电机 `id=11 (0x0B)`、寄存器 `0x170`：

- 发送：`can id = 0x60B`，数据：`00 0A 01 70`
- 接收：`can id = 0x600`，数据：`00 0B 01 70 AA AA`

其中 `AA AA` 为寄存器 16 位值（低字节在前），即：`value = data[4] | (data[5] << 8)`。

脚本默认参数已经按这个规则设置：

- `--tx-base-id 0x600`（发送 ID = 基值 + 电机ID）
- `--rx-id 0x600`（应答固定 ID）
- `--source-id 0x0A`
- `--cmd 0x01`
