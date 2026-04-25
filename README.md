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
  --source-id 0x01 \
  --arb-id 0x000 \
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
- `--source-id`：问者 ID，默认 `0x01`
- `--arb-id`：发送帧标识符 ID，默认 `0x000`
- `--timeout`：每个寄存器等待应答超时（秒），默认 `0.2`

---

## 5) 快速自测

```bash
python3 read_motor_registers.py --ids motor_ids.json --addrs register_addrs.json
```

如果你只想先确认 JSON 配置是否正确，先用默认模式（不加 `--read`）即可。
