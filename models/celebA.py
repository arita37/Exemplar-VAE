from __future__ import print_function
import torch
import torch.utils.data
import torch.nn as nn
from models.AbsModel import AbsModel
from torch.nn.utils import weight_norm

class Flatten(torch.nn.Module):
    def forward(self, x):
        batch_size = x.shape[0]
        return x.view(batch_size, -1)

class UnFlatten(torch.nn.Module):
    def __init__(self, size):
        super(UnFlatten, self).__init__()
        self.size = size

    def forward(self, x):
        batch_size = x.shape[0]
        return x.view(batch_size, *self.size)

class VAE(AbsModel):
    def __init__(self, args):
        super(VAE, self).__init__(args)

    def create_model(self, args, train_data_size=None):
        class block(nn.Module):
            def __init__(self, input_size, output_size, stride=1, kernel=3, padding=1):
                super(block, self).__init__()
                self.normalization = nn.BatchNorm2d(input_size)
                self.conv1 = weight_norm(nn.Conv2d(input_size, output_size, kernel_size=kernel,
                                                   stride=stride, padding=padding,
                                       bias=True))
                self.conv2 = weight_norm(
                    nn.Conv2d(output_size, output_size, kernel_size=kernel, stride=stride, padding=padding,
                              bias=True))
                self.activation = torch.nn.ELU()
                self.f = torch.nn.Sequential(self.activation, self.conv1, self.activation, self.conv2)

            def forward(self, x):
                return x + self.f(x)
        self.train_data_size = train_data_size

        self.q_z_layers = nn.Sequential(
            weight_norm(
                nn.Conv2d(in_channels=self.args.input_size[0], out_channels=128, kernel_size=5, stride=2, padding=2)),
            nn.ELU(),
            weight_norm(nn.Conv2d(in_channels=128, out_channels=256, kernel_size=5, stride=2, padding=2)),
            nn.ELU(),
            weight_norm(nn.Conv2d(in_channels=256, out_channels=512, kernel_size=5, stride=2, padding=2)),
            nn.ELU(),
            weight_norm(nn.Conv2d(in_channels=512, out_channels=1024, kernel_size=5, stride=2, padding=2)),
            nn.ELU(),
            Flatten()
        )

        self.q_z_mean = nn.Sequential(weight_norm(nn.Linear(1024 * 4 * 4, self.args.z1_size)))

        self.q_z_logvar = nn.Sequential(weight_norm(nn.Linear(1024 * 4 * 4, self.args.z1_size)))

        self.p_x_layers = nn.Sequential(
            weight_norm(nn.Linear(self.args.z1_size, 1024 * 4 * 4)),
            nn.ELU(),
            UnFlatten(size=[1024, 4, 4]),
            nn.Upsample(scale_factor=2),
            weight_norm(
                nn.Conv2d(in_channels=1024, out_channels=512, kernel_size=5, stride=1, padding=2)),
            nn.ELU(),
            nn.Upsample(scale_factor=2),
            weight_norm(nn.Conv2d(in_channels=512, out_channels=256, kernel_size=5, stride=1, padding=2)),
            nn.ELU(),
            nn.Upsample(scale_factor=2),
            weight_norm(
                nn.Conv2d(in_channels=256, out_channels=128, kernel_size=5, stride=1, padding=2)),
            nn.ELU(),
            nn.Upsample(scale_factor=2),
        )

        if self.args.input_type == 'gray' or self.args.input_type == 'continuous':
            self.p_x_mean = nn.Sequential(nn.Sigmoid(), nn.Conv2d(in_channels=128, out_channels=3, kernel_size=5, stride=1, padding=2))

