from krita import Extension, Krita
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from .inxdocument import INXDocument


class KritaInxExport(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def exportDocument(self):
        doc = Krita.instance().activeDocument()
        if doc is not None:
            name = doc.name()
            if not name:
                file_path = doc.fileName()
                name = file_path.split("/")[-1][:-4]
            directory= name + ".inx"
            fileName = QFileDialog.getSaveFileName(caption="Save As...", directory=directory, filter="Inochi Creator Project (*.inx)")[0]
            if fileName:
                inx = INXDocument(doc)
                inx.save(fileName)
                msg = QMessageBox(QMessageBox.Information, "File Saved!", "Some layers are displayed wrong in 'Inochi Creator', to fix it click on \"Tools > Premultiply Textures\"")
                msg.setWindowModality(2)
                msg.exec()

    def createActions(self, window):
        action = window.createAction("inx-export", "Export INX file", "tools/scripts")
        action.triggered.connect(self.exportDocument)

Krita.instance().addExtension(KritaInxExport(Krita.instance()))
