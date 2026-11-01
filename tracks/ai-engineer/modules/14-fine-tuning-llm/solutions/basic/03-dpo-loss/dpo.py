import torch
import torch.nn.functional as F
from torch import nn

IGNORE_INDEX = -100


def sequence_logps(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """Tổng log-xác suất của các token có label (khác -100) của mỗi chuỗi, shape (batch,)."""
    logits = logits[:, :-1].float()
    labels = labels[:, 1:]
    mask = labels != IGNORE_INDEX
    safe = labels.masked_fill(~mask, 0)
    token_logps = torch.gather(logits.log_softmax(-1), 2, safe.unsqueeze(-1)).squeeze(-1)
    return (token_logps * mask).sum(-1)


def dpo_loss(policy_chosen: torch.Tensor, policy_rejected: torch.Tensor, ref_chosen: torch.Tensor,
             ref_rejected: torch.Tensor, beta: float = 0.1) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    chosen_logratio = policy_chosen - ref_chosen
    rejected_logratio = policy_rejected - ref_rejected
    loss = -F.logsigmoid(beta * (chosen_logratio - rejected_logratio)).mean()
    return loss, beta * chosen_logratio.detach(), beta * rejected_logratio.detach()


def _logps(model: nn.Module, input_ids: torch.Tensor, attention_mask: torch.Tensor,
           labels: torch.Tensor) -> torch.Tensor:
    return sequence_logps(model(input_ids=input_ids, attention_mask=attention_mask).logits, labels)


def dpo_step(policy: nn.Module, reference: nn.Module, batch: dict[str, torch.Tensor], beta: float,
             optimizer: torch.optim.Optimizer) -> dict[str, float]:
    with torch.no_grad():
        ref_c = _logps(reference, batch["chosen_input_ids"], batch["chosen_attention_mask"], batch["chosen_labels"])
        ref_r = _logps(reference, batch["rejected_input_ids"], batch["rejected_attention_mask"],
                       batch["rejected_labels"])
    pol_c = _logps(policy, batch["chosen_input_ids"], batch["chosen_attention_mask"], batch["chosen_labels"])
    pol_r = _logps(policy, batch["rejected_input_ids"], batch["rejected_attention_mask"], batch["rejected_labels"])
    loss, chosen_rewards, rejected_rewards = dpo_loss(pol_c, pol_r, ref_c, ref_r, beta)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    margin = chosen_rewards - rejected_rewards
    return {"loss": loss.item(), "reward_margin": margin.mean().item(),
            "reward_accuracy": (margin > 0).float().mean().item()}
