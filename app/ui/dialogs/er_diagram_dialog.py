"""ER 图独立弹窗 (非模态)。

加载顺序: schema_polished.png → schema.svg → schema.png → 占位文本。
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QScrollArea, QPushButton, QHBoxLayout,
    QFileDialog, QMessageBox,
)

from app.config import load_config


class ErDiagramDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ER 图 — 学生成绩数据库")
        self.setModal(False)
        self.resize(1100, 760)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: white;")

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.label)
        self.scroll.setWidgetResizable(False)

        self.btn_reload = QPushButton("重新加载")
        self.btn_save   = QPushButton("另存为图片")
        self.btn_zoom_in  = QPushButton("放大")
        self.btn_zoom_out = QPushButton("缩小")
        self.btn_fit      = QPushButton("适应窗口")
        self.btn_reload.clicked.connect(self.reload)
        self.btn_save.clicked.connect(self._save_as)
        self.btn_zoom_in.clicked.connect(lambda: self._zoom(1.25))
        self.btn_zoom_out.clicked.connect(lambda: self._zoom(0.8))
        self.btn_fit.clicked.connect(self._fit)

        toolbar = QHBoxLayout()
        for b in (self.btn_reload, self.btn_zoom_out,
                  self.btn_fit, self.btn_zoom_in, self.btn_save):
            toolbar.addWidget(b)
        toolbar.addStretch(1)

        self.source_label = QLabel("")
        self.source_label.setStyleSheet("color: #666; padding: 4px;")

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self.scroll, 1)
        layout.addWidget(self.source_label)

        self._pix: QPixmap | None = None
        self._scale: float = 1.0
        self._loaded_path: Path | None = None
        self.reload()

    def reload(self) -> None:
        er_dir = load_config().paths.docs_dir / "er"
        candidates = [
            er_dir / "schema_polished.png",
            er_dir / "schema.svg",
            er_dir / "schema.png",
        ]
        for p in candidates:
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self._pix = pix
                    self._loaded_path = p
                    self._scale = 1.0
                    self._apply_scale()
                    label = "润色版" if "polished" in p.name else "Mermaid base"
                    self.source_label.setText(f"{label}: {p}")
                    return

        self._pix = None
        self.label.clear()
        self.label.setText(
            "ER 图尚未渲染。请按以下任一方式生成:\n\n"
            "  · 在 https://mermaid.live 粘贴 docs/er/schema.mmd, 导出 PNG/SVG;\n"
            "  · npm i -g @mermaid-js/mermaid-cli && mmdc -i docs/er/schema.mmd -o docs/er/schema.png\n"
            "  · 详见 docs/er/POLISH_GUIDE.md"
        )
        self.label.setMinimumSize(900, 500)
        self.source_label.setText("(未找到 ER 图文件)")

    def _apply_scale(self) -> None:
        if self._pix is None:
            return
        sz = self._pix.size() * self._scale
        scaled = self._pix.scaled(sz, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled)
        self.label.resize(scaled.size())

    def _zoom(self, factor: float) -> None:
        self._scale = max(0.1, min(4.0, self._scale * factor))
        self._apply_scale()

    def _fit(self) -> None:
        if self._pix is None:
            return
        w = self.scroll.viewport().width() - 20
        h = self.scroll.viewport().height() - 20
        if self._pix.width() <= 0:
            return
        self._scale = min(w / self._pix.width(), h / self._pix.height())
        self._apply_scale()

    def _save_as(self) -> None:
        if self._pix is None:
            QMessageBox.information(self, "提示", "尚未加载 ER 图")
            return
        fn, _ = QFileDialog.getSaveFileName(self, "保存 ER 图", "ER.png",
                                            "PNG (*.png);;JPG (*.jpg)")
        if fn:
            self._pix.save(fn)
