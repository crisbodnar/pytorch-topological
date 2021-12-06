"""Minimise functions based on Vietoris--Rips complexes."""

from gph import ripser_parallel
from torch import nn

import torch


class ModelSpaceLoss(nn.Module):
    """Optimise persistence-based functions on a Vietoris--Rips complex.

    This module should be used if a 'model space' $Y$ is present, and
    a loss function between the two spaces should be optimised.
    """

    def __init__(self, X, Y, loss):
        """Initialise new module.

        Parameters
        ----------
        X : `np.array`
            Input point cloud, typically denoted as the 'source' point
            cloud that can be adjusted.

        Y : `np.array`
            Target point cloud. Will be considered fixed and not
            trainable at all.

        loss : `nn.Module`
            Loss to evaluate between the source and the target point
            cloud. Will be initialised within this function.
        """
        super().__init__()

        self.X = nn.Parameter(torch.as_tensor(X), requires_grad=True)
        self.Y = Y

        # TODO: make configurable
        self.pd_target = ripser_parallel(self.Y)['dgms']
        self.pd_target = [torch.as_tensor(pd) for pd in self.pd_target]

        self.loss = loss(Y=self.Y)

    def forward(self):
        """Implement forward pass of the loss.

        The forward pass entails evaluating the provided function on the
        persistence diagrams obtained from the current source point
        cloud.

        Returns
        -------
        Loss
        """
        X = self.X

        generators = ripser_parallel(
            X.detach(),
            return_generators=True
        )['gens']

        # TODO: Is this always required? Can we calculate this in
        # a smarter fashion?
        #
        # Calculate distances in the source space and select the
        # appropriate tuples later on.
        source_distances = torch.cdist(X, X, p=2)

        generators_0d = generators[0]
        generators_1d = generators[1]

        edge_indices_0d = generators_0d[:, 1:]
        edge_indices_1d = generators_1d[0][:, 0:]

        destroyers_0d = source_distances[
            edge_indices_0d[:, 0], edge_indices_0d[:, 1]
        ]

        creators_1d = source_distances[
            edge_indices_1d[:, 0], edge_indices_1d[:, 1]
        ]

        destroyers_1d = source_distances[
            edge_indices_1d[:, 2], edge_indices_1d[:, 3]
        ]

        persistence_0d = destroyers_0d
        persistence_1d = destroyers_1d - creators_1d

        persistence_diagram_0d = torch.stack(
            (torch.zeros_like(persistence_0d), destroyers_0d), 1
        )

        persistence_diagram_1d = torch.stack(
            (creators_1d, destroyers_1d), 1
        )

        loss = self.loss(
            [persistence_diagram_0d, persistence_diagram_1d]
        )

        return loss
