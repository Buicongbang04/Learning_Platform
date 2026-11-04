import time

import numpy as np
import triton_python_backend_utils as pb_utils

COEF = np.array([2.1, 0.35, 0.8], dtype=np.float32)
SECONDS_PER_EXECUTE = 0.02


class TritonPythonModel:
    def execute(self, requests):
        time.sleep(SECONDS_PER_EXECUTE)
        responses = []
        for request in requests:
            rows = pb_utils.get_input_tensor_by_name(request, "INPUT").as_numpy()
            predictions = (4.0 + rows @ COEF).astype(np.float32).reshape(-1, 1)
            responses.append(pb_utils.InferenceResponse([pb_utils.Tensor("OUTPUT", predictions)]))
        return responses
