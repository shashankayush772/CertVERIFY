"""
Train CertForgeryNet on a folder dataset.

Expected layout::

    data_root/
      authentic/
        *.jpg, *.png, ...
      forged/
        *.jpg, *.png, ...

Usage::

    python -m backend.ml.train --data-dir ./data/certs --epochs 5 --out ./models/forgery.pt
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from backend.ml.predict import CertForgeryNet, default_image_transform


def build_loaders(data_dir: Path, batch_size: int, image_size: int, num_workers: int = 0):
    tfm = default_image_transform(image_size)
    dataset = datasets.ImageFolder(str(data_dir), transform=tfm)
    if len(dataset.classes) != 2:
        raise ValueError(f"Expected 2 classes (authentic, forged), got: {dataset.classes}")
    n = len(dataset)
    n_train = int(0.9 * n)
    n_val = n - n_train
    train_ds, val_ds = torch.utils.data.random_split(
        dataset,
        [n_train, n_val],
        generator=torch.Generator().manual_seed(42),
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )
    return train_loader, val_loader, dataset.classes


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(images)
        loss = criterion(logits, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * images.size(0)
    return total_loss / max(1, len(loader.dataset))


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)
        logits = model(images)
        loss = criterion(logits, targets)
        total_loss += loss.item() * images.size(0)
        preds = logits.argmax(dim=1)
        correct += int((preds == targets).sum().item())
        total += targets.size(0)
    acc = correct / max(1, total)
    avg_loss = total_loss / max(1, total)
    return avg_loss, acc


def main() -> None:
    parser = argparse.ArgumentParser(description="Train CertVerify forgery classifier")
    parser.add_argument("--data-dir", type=Path, required=True, help="ImageFolder root with class subdirs")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--out", type=Path, default=Path("models/forgery.pt"))
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, class_names = build_loaders(
        args.data_dir,
        batch_size=args.batch_size,
        image_size=args.image_size,
    )

    model = CertForgeryNet(num_classes=len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    best_acc = 0.0

    for epoch in range(1, args.epochs + 1):
        tr_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        va_loss, va_acc = evaluate(model, val_loader, criterion, device)
        print(f"Epoch {epoch}/{args.epochs}  train_loss={tr_loss:.4f}  val_loss={va_loss:.4f}  val_acc={va_acc:.4f}")
        if va_acc >= best_acc:
            best_acc = va_acc
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "class_names": class_names,
                    "image_size": args.image_size,
                },
                args.out,
            )
            print(f"  saved checkpoint -> {args.out}")


if __name__ == "__main__":
    main()
