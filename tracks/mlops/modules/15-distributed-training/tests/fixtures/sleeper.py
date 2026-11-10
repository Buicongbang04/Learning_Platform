import sys
import time
from pathlib import Path

import torch.distributed as dist

dist.init_process_group("gloo")
Path(sys.argv[1], f"ready{dist.get_rank()}").write_text("1")
time.sleep(60)
dist.destroy_process_group()
