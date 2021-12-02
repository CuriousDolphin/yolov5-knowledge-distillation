# thanks https://github.com/Syencil/mobile-yolov5-pruning-distillation/blob/master/utils/utils.py
import numpy as np
import torch
import torch.nn as nn

def compute_distillation_output_loss(p, t_p, model, loss):
    t_ft = torch.cuda.FloatTensor if t_p[0].is_cuda else torch.Tensor
    t_lcls, t_lbox, t_lobj = t_ft([0]), t_ft([0]), t_ft([0])
    h = model.hyp  # hyperparameters
    red = 'mean'  # Loss reduction (sum or mean)
    if red != "mean":
        raise NotImplementedError("reduction must be mean in distillation mode!")

    DboxLoss = nn.MSELoss(reduction="none")
    DclsLoss = nn.MSELoss(reduction="none")
    DobjLoss = nn.MSELoss(reduction="none")
    # per output
    for i, pi in enumerate(p):  # layer index, layer predictions
        t_pi = t_p[i]
        t_obj_scale = t_pi[..., 4].sigmoid()

        # BBox
        b_obj_scale = t_obj_scale.unsqueeze(-1).repeat(1, 1, 1, 1, 4)
        t_lbox += torch.mean(DboxLoss(pi[..., :4], t_pi[..., :4]) * b_obj_scale)

        # Class
        if model.nc > 1:  # cls loss (only if multiple classes)
            c_obj_scale = t_obj_scale.unsqueeze(-1).repeat(1, 1, 1, 1, model.nc)
            # t_lcls += torch.mean(c_obj_scale * (pi[..., 5:] - t_pi[..., 5:]) ** 2)
            t_lcls += torch.mean(DclsLoss(pi[..., 5:], t_pi[..., 5:]) * c_obj_scale)

        # t_lobj += torch.mean(t_obj_scale * (pi[..., 4] - t_pi[..., 4]) ** 2)
        t_lobj += torch.mean(DobjLoss(pi[..., 4], t_pi[..., 4]) * t_obj_scale)
    t_lbox *= h['box'] 
    t_lobj *= h['obj'] 
    t_lcls *= h['cls'] 
    bs = p[0].shape[0]  # batch size
    loss += (t_lobj + t_lbox + t_lcls) * bs
    return loss


def compute_distillation_feature_loss(s_f, t_f, model, loss):
    h = model.hyp  # hyperparameters
    ft = torch.cuda.FloatTensor if s_f[0].is_cuda else torch.Tensor
    dl_1, dl_2, dl_3 = ft([0]), ft([0]), ft([0])

    loss_func1 = nn.MSELoss(reduction="mean")
    loss_func2 = nn.MSELoss(reduction="mean")
    loss_func3 = nn.MSELoss(reduction="mean")

    dl_1 += loss_func1(s_f[0], t_f[0])
    dl_2 += loss_func2(s_f[1], t_f[1])
    dl_3 += loss_func3(s_f[2], t_f[2])

    bs = s_f[0].shape[0]
    dl_1 *= h['dist'] / 20
    dl_2 *= h['dist'] / 20
    dl_3 *= h['dist'] / 20
    loss += (dl_1 + dl_2 + dl_3) * bs
    return loss
