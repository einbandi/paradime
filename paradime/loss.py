import torch
import uuid

import paradime.relations as pdrel
import paradime.relationdata as pdreldata
import paradime.models as pdmod
from paradime.types import LossFun, Tensor

class Loss(torch.nn.Module):

    _prefix = 'loss'

    def __init__(self,
        name: str = None):
        super().__init__()

        if name is None:
            self.name = self._prefix + str(uuid.uuid4())
        else:
            self.name = name

    def forward(self,
        model: pdmod.Model,
        hd_relations: pdreldata.RelationData,
        ld_relations: pdrel.Relations,
        batch: dict[str, torch.Tensor],
        ) -> torch.Tensor:

        raise NotImplementedError()


class RelationLoss(Loss):

    _prefix = 'rel_loss'

    def __init__(self,
        loss_function: LossFun,
        name: str = None,
        ):
        super().__init__(name)

        self.loss_function = loss_function

    def forward(self,
        model: pdmod.Model,
        hd_relations: pdreldata.RelationData,
        ld_relations: pdrel.Relations,
        batch: dict[str, torch.Tensor],
        ) -> torch.Tensor:


        assert isinstance(batch['indices'], torch.IntTensor)

        return self.loss_function(
            hd_relations.sub(batch['indices']),
            ld_relations.compute_relations(
                model.embed(batch['data'])
            ).data
        )
    
class ClassificationLoss(Loss):

    _prefix = 'class_loss'

    def __init__(self,
        label_key: str = 'labels',
        loss_function: LossFun = torch.nn.CrossEntropyLoss(),
        name: str = None,
        ):
        super().__init__(name)

        self.loss_function = loss_function
    
    def forward(self,
        model: pdmod.Model,
        hd_relations: pdreldata.RelationData,
        ld_relations: pdrel.Relations,
        batch: dict[str, torch.Tensor],
        ) -> torch.Tensor:

        return self.loss_function(
            model.classify(batch['data']),
            batch['labels']
        )

class PositionLoss(Loss):

    _prefix = 'pos_loss'

    def __init__(self,
        position_key: str = 'pos',
        loss_function: LossFun = torch.nn.MSELoss(),
        name: str = None,
        ):
        super().__init__(name)

        self.loss_function = loss_function
    
    def forward(self,
        model: pdmod.Model,
        hd_relations: pdreldata.RelationData,
        ld_relations: pdrel.Relations,
        batch: dict[str, torch.Tensor],
        ) -> torch.Tensor:

        return self.loss_function(
            model.embed(batch['data']),
            batch['pos']
        )
    
class ReconstructionLoss(Loss):

    _prefix = 'recon_loss'

    def __init__(self,
        loss_function: LossFun = torch.nn.MSELoss(),
        name: str = None
        ):
        super().__init__(name)

        self.loss_function = loss_function

    def forward(self,
        model: pdmod.Model,
        hd_relations: pdreldata.RelationData,
        ld_relations: pdrel.Relations,
        batch: dict[str, torch.Tensor],
        ) -> torch.Tensor:

        return self.loss_function(
            batch['data'],
            model.decode(model.encode(batch['data'])),
        )

class CompoundLoss(Loss):

    _prefix = 'comp_loss'

    def __init__(self,
        losses: list[Loss],
        weights: Tensor,
        name: str = None):
        super().__init__(name)

        self.losses = losses
        self.weights = weights

        if self.weights is None:
            self.weights = torch.ones(len(losses))
        elif len(self.weights) != len(self.losses):
            raise ValueError(
                "Size mismatch between losses and weights."
            )
        
    def forward(self,
        model: pdmod.Model,
        hd_relations: pdreldata.RelationData,
        ld_relations: pdrel.Relations,
        batch: dict[str, torch.Tensor],
        ) -> torch.Tensor:

        total_loss = torch.tensor(0.)

        for l,w in zip(self.losses, self.weights):
            total_loss += w * l(model, hd_relations, ld_relations, batch)

        return total_loss