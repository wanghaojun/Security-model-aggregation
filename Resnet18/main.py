import torch
from Resnet18 import model as modeltool
from Resnet18 import dataset
epoch = 100
lr = 0.001
momentum = 0.0001
batch_size = 32
train_dataset, eval_dataset = dataset.get_dataset('../data/', 'cifar')
model = modeltool.get_model()
def train():
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size,)
    optimizer = torch.optim.SGD(model.parameters(), lr=lr,
                                momentum=momentum)
    model.train()
    for e in range(epoch):

        for batch_id, batch in enumerate(train_loader):
            data, target = batch

            if torch.cuda.is_available():
                data = data.cuda()
                target = target.cuda()

            optimizer.zero_grad()
            output = model(data)
            loss = torch.nn.functional.cross_entropy(output, target)
            loss.backward()

            optimizer.step()
        acc, loss = model_eval()
        print("Epoch %d, acc: %f, loss: %f\n" % (e, acc, loss))


def model_eval():
    model.eval()
    eval_loader = torch.utils.data.DataLoader(eval_dataset, batch_size=batch_size, shuffle=True)
    total_loss = 0.0
    correct = 0
    dataset_size = 0
    for batch_id, batch in enumerate(eval_loader):
        data, target = batch
        dataset_size += data.size()[0]

        if torch.cuda.is_available():
            data = data.cuda()
            target = target.cuda()

        output = model(data)

        total_loss += torch.nn.functional.cross_entropy(output, target, reduction='sum').item()  # sum up batch loss
        pred = output.data.max(1)[1]  # get the index of the max log-probability
        correct += pred.eq(target.data.view_as(pred)).cpu().sum().item()

    acc = 100.0 * (float(correct) / float(dataset_size))
    total_l = total_loss / dataset_size
    return acc, total_l
if __name__ == '__main__':
    train()
