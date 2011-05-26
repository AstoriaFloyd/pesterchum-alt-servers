from PyQt4 import QtGui, QtCore
import re

from os import remove
from generic import RightClickList, RightClickTree, MultiTextDialog
from dataobjs import pesterQuirk, PesterProfile
from memos import TimeSlider, TimeInput
from version import _pcVersion

class PesterQuirkItem(QtGui.QTreeWidgetItem):
    def __init__(self, quirk):
        parent = None
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self.quirk = quirk
        self.setText(0, unicode(quirk))
    def update(self, quirk):
        self.quirk = quirk
        self.setText(0, unicode(quirk))
    def __lt__(self, quirkitem):
        """Sets the order of quirks if auto-sorted by Qt. Obsolete now."""
        if self.quirk.type == "prefix":
            return True
        elif (self.quirk.type == "replace" or self.quirk.type == "regexp") and \
                quirkitem.type == "suffix":
            return True
        else:
            return False
class PesterQuirkList(QtGui.QTreeWidget):
    def __init__(self, mainwindow, parent):
        QtGui.QTreeWidget.__init__(self, parent)
        self.resize(400, 200)
        # make sure we have access to mainwindow info like profiles
        self.mainwindow = mainwindow
        self.setStyleSheet("background:black; color:white;")

        self.connect(self, QtCore.SIGNAL('itemChanged(QTreeWidgetItem *, int)'),
                     self, QtCore.SLOT('changeCheckState()'))

        for q in mainwindow.userprofile.quirks:
            item = PesterQuirkItem(q)
            self.addItem(item, False)
        self.changeCheckState()
        #self.setDragEnabled(True)
        #self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)
        self.setSortingEnabled(False)
        self.setIndentation(15)
        self.header().hide()

    def addItem(self, item, new=True):
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        if item.quirk.on:
            item.setCheckState(0, 2)
        else:
            item.setCheckState(0, 0)
        if new:
            curgroup = self.currentItem()
            if curgroup:
                if curgroup.parent(): curgroup = curgroup.parent()
                item.quirk.quirk["group"] = item.quirk.group = curgroup.text(0)
        found = self.findItems(item.quirk.group, QtCore.Qt.MatchExactly)
        if len(found) > 0:
            found[0].addChild(item)
        else:
            child_1 = QtGui.QTreeWidgetItem([item.quirk.group])
            self.addTopLevelItem(child_1)
            child_1.setFlags(child_1.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            child_1.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.DontShowIndicatorWhenChildless)
            child_1.setCheckState(0,0)
            child_1.setExpanded(True)
            child_1.addChild(item)

    def currentQuirk(self):
        if type(self.currentItem()) is PesterQuirkItem:
            return self.currentItem()
        else: return None

    @QtCore.pyqtSlot()
    def upShiftQuirk(self):
        found = self.findItems(self.currentItem().text(0), QtCore.Qt.MatchExactly)
        if len(found): # group
            i = self.indexOfTopLevelItem(found[0])
            if i > 0:
                expand = found[0].isExpanded()
                shifted_item = self.takeTopLevelItem(i)
                self.insertTopLevelItem(i-1, shifted_item)
                shifted_item.setExpanded(expand)
                self.setCurrentItem(shifted_item)
        else: # quirk
            found = self.findItems(self.currentItem().text(0), QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
            for f in found:
                if not f.isSelected(): continue
                if not f.parent(): continue
                i = f.parent().indexOfChild(f)
                if i > 0: # keep in same group
                    p = f.parent()
                    shifted_item = f.parent().takeChild(i)
                    p.insertChild(i-1, shifted_item)
                    self.setCurrentItem(shifted_item)
                else: # move to another group
                    j = self.indexOfTopLevelItem(f.parent())
                    if j <= 0: continue
                    shifted_item = f.parent().takeChild(i)
                    self.topLevelItem(j-1).addChild(shifted_item)
                    self.setCurrentItem(shifted_item)
            self.changeCheckState()

    @QtCore.pyqtSlot()
    def downShiftQuirk(self):
        found = self.findItems(self.currentItem().text(0), QtCore.Qt.MatchExactly)
        if len(found): # group
            i = self.indexOfTopLevelItem(found[0])
            if i < self.topLevelItemCount()-1 and i >= 0:
                expand = found[0].isExpanded()
                shifted_item = self.takeTopLevelItem(i)
                self.insertTopLevelItem(i+1, shifted_item)
                shifted_item.setExpanded(expand)
                self.setCurrentItem(shifted_item)
        else: # quirk
            found = self.findItems(self.currentItem().text(0), QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
            for f in found:
                if not f.isSelected(): continue
                if not f.parent(): continue
                i = f.parent().indexOfChild(f)
                if i < f.parent().childCount()-1 and i >= 0:
                    p = f.parent()
                    shifted_item = f.parent().takeChild(i)
                    p.insertChild(i+1, shifted_item)
                    self.setCurrentItem(shifted_item)
                else:
                    j = self.indexOfTopLevelItem(f.parent())
                    if j >= self.topLevelItemCount()-1 or j < 0: continue
                    shifted_item = f.parent().takeChild(i)
                    self.topLevelItem(j+1).insertChild(0, shifted_item)
                    self.setCurrentItem(shifted_item)
            self.changeCheckState()

    @QtCore.pyqtSlot()
    def removeCurrent(self):
        i = self.currentItem()
        found = self.findItems(i.text(0), QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
        for f in found:
            if not f.isSelected(): continue
            if not f.parent(): # group
                msgbox = QtGui.QMessageBox()
                msgbox.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])
                msgbox.setWindowTitle("WARNING!")
                msgbox.setInformativeText("Are you sure you want to delete the quirk group: %s" % (f.text(0)))
                msgbox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
                ret = msgbox.exec_()
                if ret == QtGui.QMessageBox.Ok:
                    self.takeTopLevelItem(self.indexOfTopLevelItem(f))
            else:
                f.parent().takeChild(f.parent().indexOfChild(f))

    @QtCore.pyqtSlot()
    def addQuirkGroup(self):
        if not hasattr(self, 'addgroupdialog'):
            self.addgroupdialog = None
        if not self.addgroupdialog:
            (gname, ok) = QtGui.QInputDialog.getText(self, "Add Group", "Enter a name for the new quirk group:")
            if ok:
                gname = unicode(gname)
                if re.search("[^A-Za-z0-9_\s]", gname) is not None:
                    msgbox = QtGui.QMessageBox()
                    msgbox.setInformativeText("THIS IS NOT A VALID GROUP NAME")
                    msgbox.setStandardButtons(QtGui.QMessageBox.Ok)
                    ret = msgbox.exec_()
                    self.addgroupdialog = None
                    return
                found = self.findItems(gname, QtCore.Qt.MatchExactly)
                if found:
                    msgbox = QtGui.QMessageBox()
                    msgbox.setInformativeText("THIS QUIRK GROUP ALREADY EXISTS")
                    msgbox.setStandardButtons(QtGui.QMessageBox.Ok)
                    ret = msgbox.exec_()
                    return
                child_1 = QtGui.QTreeWidgetItem([gname])
                self.addTopLevelItem(child_1)
                child_1.setFlags(child_1.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                child_1.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.DontShowIndicatorWhenChildless)
                child_1.setCheckState(0,0)
                child_1.setExpanded(True)

            self.addgroupdialog = None

    @QtCore.pyqtSlot()
    def changeCheckState(self):
        index = self.indexOfTopLevelItem(self.currentItem())
        if index == -1:
            for i in range(self.topLevelItemCount()):
                allChecked = True
                noneChecked = True
                for j in range(self.topLevelItem(i).childCount()):
                    if self.topLevelItem(i).child(j).checkState(0):
                        noneChecked = False
                    else:
                        allChecked = False
                if allChecked:    self.topLevelItem(i).setCheckState(0, 2)
                elif noneChecked: self.topLevelItem(i).setCheckState(0, 0)
                else:             self.topLevelItem(i).setCheckState(0, 1)
        else:
            state = self.topLevelItem(index).checkState(0)
            for j in range(self.topLevelItem(index).childCount()):
                self.topLevelItem(index).child(j).setCheckState(0, state)

class MispellQuirkDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle("MISPELLER")
        layout_1 = QtGui.QHBoxLayout()
        zero = QtGui.QLabel("1%", self)
        hund = QtGui.QLabel("100%", self)
        self.current = QtGui.QLabel("50%", self)
        self.current.setAlignment(QtCore.Qt.AlignHCenter)
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(50)
        self.connect(self.slider, QtCore.SIGNAL('valueChanged(int)'),
                     self, QtCore.SLOT('printValue(int)'))
        layout_1.addWidget(zero)
        layout_1.addWidget(self.slider)
        layout_1.addWidget(hund)

        self.ok = QtGui.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('accept()'))
        self.cancel = QtGui.QPushButton("CANCEL", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        layout_ok = QtGui.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = QtGui.QVBoxLayout()
        layout_0.addLayout(layout_1)
        layout_0.addWidget(self.current)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)
    def getPercentage(self):
        r = self.exec_()
        if r == QtGui.QDialog.Accepted:
            retval = {"percentage": self.slider.value()}
            return retval
        else:
            return None

    @QtCore.pyqtSlot(int)
    def printValue(self, value):
        self.current.setText(str(value)+"%")

class RandomQuirkDialog(MultiTextDialog):
    def __init__(self, parent, values={}):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle("RANDOM QUIRK")
        self.inputs = {}
        layout_1 = QtGui.QHBoxLayout()
        regexpl = QtGui.QLabel("REGEXP:", self)
        self.regexp = QtGui.QLineEdit(values.get("regexp",""), self)
        layout_1.addWidget(regexpl)
        layout_1.addWidget(self.regexp)
        replacewithl = QtGui.QLabel("REPLACE WITH:", self)

        layout_2 = QtGui.QVBoxLayout()
        layout_3 = QtGui.QHBoxLayout()
        self.replacelist = QtGui.QListWidget(self)
        for v in values.get("list", []):
            item = QtGui.QListWidgetItem(v, self.replacelist)
        self.replaceinput = QtGui.QLineEdit(self)
        addbutton = QtGui.QPushButton("ADD", self)
        self.connect(addbutton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('addRandomString()'))
        removebutton = QtGui.QPushButton("REMOVE", self)
        self.connect(removebutton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('removeRandomString()'))
        layout_3.addWidget(addbutton)
        layout_3.addWidget(removebutton)
        layout_2.addWidget(self.replacelist)
        layout_2.addWidget(self.replaceinput)
        layout_2.addLayout(layout_3)
        layout_1.addLayout(layout_2)

        self.ok = QtGui.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('accept()'))
        self.cancel = QtGui.QPushButton("CANCEL", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        layout_ok = QtGui.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = QtGui.QVBoxLayout()
        layout_0.addLayout(layout_1)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)

    def getText(self):
        r = self.exec_()
        if r == QtGui.QDialog.Accepted:
            randomlist = [unicode(self.replacelist.item(i).text())
                          for i in range(0,self.replacelist.count())]
            retval = {"from": unicode(self.regexp.text()),
                      "randomlist": randomlist }
            return retval
        else:
            return None


    @QtCore.pyqtSlot()
    def addRandomString(self):
        text = unicode(self.replaceinput.text())
        item = QtGui.QListWidgetItem(text, self.replacelist)
        self.replaceinput.setText("")
        self.replaceinput.setFocus()
    @QtCore.pyqtSlot()
    def removeRandomString(self):
        if not self.replacelist.currentItem():
            return
        else:
            self.replacelist.takeItem(self.replacelist.currentRow())
        self.replaceinput.setFocus()

class PesterChooseQuirks(QtGui.QDialog):
    def __init__(self, config, theme, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.mainwindow = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.setWindowTitle("Set Quirks")

        self.quirkList = PesterQuirkList(self.mainwindow, self)

        self.addPrefixButton = QtGui.QPushButton("ADD PREFIX", self)
        self.connect(self.addPrefixButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('addPrefixDialog()'))
        self.addSuffixButton = QtGui.QPushButton("ADD SUFFIX", self)
        self.connect(self.addSuffixButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('addSuffixDialog()'))
        self.addSimpleReplaceButton = QtGui.QPushButton("SIMPLE REPLACE", self)
        self.connect(self.addSimpleReplaceButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('addSimpleReplaceDialog()'))
        self.addRegexpReplaceButton = QtGui.QPushButton("REGEXP REPLACE", self)
        self.connect(self.addRegexpReplaceButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('addRegexpDialog()'))
        self.addRandomReplaceButton = QtGui.QPushButton("RANDOM REPLACE", self)
        self.connect(self.addRandomReplaceButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('addRandomDialog()'))
        self.addMispellingButton = QtGui.QPushButton("MISPELLER", self)
        self.connect(self.addMispellingButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('addSpellDialog()'))

        self.upShiftButton = QtGui.QPushButton("^", self)
        self.downShiftButton = QtGui.QPushButton("v", self)
        self.upShiftButton.setToolTip("Move quirk up one")
        self.downShiftButton.setToolTip("Move quirk down one")
        self.connect(self.upShiftButton, QtCore.SIGNAL('clicked()'),
                     self.quirkList, QtCore.SLOT('upShiftQuirk()'))
        self.connect(self.downShiftButton, QtCore.SIGNAL('clicked()'),
                    self.quirkList, QtCore.SLOT('downShiftQuirk()'))

        self.newGroupButton = QtGui.QPushButton("*", self)
        self.newGroupButton.setToolTip("New Quirk Group")
        self.connect(self.newGroupButton, QtCore.SIGNAL('clicked()'),
                     self.quirkList, QtCore.SLOT('addQuirkGroup()'))

        layout_quirklist = QtGui.QHBoxLayout() #the nude layout quirklist
        layout_shiftbuttons = QtGui.QVBoxLayout() #the shift button layout
        layout_shiftbuttons.addWidget(self.upShiftButton)
        layout_shiftbuttons.addWidget(self.newGroupButton)
        layout_shiftbuttons.addWidget(self.downShiftButton)
        layout_quirklist.addWidget(self.quirkList)
        layout_quirklist.addLayout(layout_shiftbuttons)

        layout_1 = QtGui.QHBoxLayout()
        layout_1.addWidget(self.addPrefixButton)
        layout_1.addWidget(self.addSuffixButton)
        layout_1.addWidget(self.addSimpleReplaceButton)
        layout_2 = QtGui.QHBoxLayout()
        layout_2.addWidget(self.addRegexpReplaceButton)
        layout_2.addWidget(self.addRandomReplaceButton)
        layout_2.addWidget(self.addMispellingButton)

        self.editSelectedButton = QtGui.QPushButton("EDIT", self)
        self.connect(self.editSelectedButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('editSelected()'))
        self.removeSelectedButton = QtGui.QPushButton("REMOVE", self)
        self.connect(self.removeSelectedButton, QtCore.SIGNAL('clicked()'),
                     self.quirkList, QtCore.SLOT('removeCurrent()'))
        layout_3 = QtGui.QHBoxLayout()
        layout_3.addWidget(self.editSelectedButton)
        layout_3.addWidget(self.removeSelectedButton)

        self.ok = QtGui.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('accept()'))
        self.cancel = QtGui.QPushButton("CANCEL", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        layout_ok = QtGui.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = QtGui.QVBoxLayout()
        layout_0.addLayout(layout_quirklist)
        layout_0.addLayout(layout_1)
        layout_0.addLayout(layout_2)
        layout_0.addLayout(layout_3)
        layout_0.addLayout(layout_ok)
        self.setLayout(layout_0)

    def quirks(self):
        u = []
        for i in range(self.quirkList.topLevelItemCount()):
            for j in range(self.quirkList.topLevelItem(i).childCount()):
                u.append(self.quirkList.topLevelItem(i).child(j).quirk)
        return u
        #return [self.quirkList.item(i).quirk for i in range(self.quirkList.count())]

    @QtCore.pyqtSlot()
    def editSelected(self):
        q = self.quirkList.currentQuirk()
        if not q: return
        quirk = q.quirk
        if quirk.type == "prefix":
            self.addPrefixDialog(q)
        elif quirk.type == "suffix":
            self.addSuffixDialog(q)
        elif quirk.type == "replace":
            self.addSimpleReplaceDialog(q)
        elif quirk.type == "regexp":
            self.addRegexpDialog(q)
        elif quirk.type == "random":
            self.addRandomDialog(q)
        elif quirk.type == "spelling":
            self.addSpellDialog(q)

    @QtCore.pyqtSlot()
    def addPrefixDialog(self, qitem=None):
        d = {"label": "Value:", "inputname": "value" }
        if qitem is not None:
            d["value"] = qitem.quirk.quirk["value"]
        pdict = MultiTextDialog("ENTER PREFIX", self, d).getText()
        if pdict is None:
            return
        pdict["type"] = "prefix"
        prefix = pesterQuirk(pdict)
        if qitem is None:
            pitem = PesterQuirkItem(prefix)
            self.quirkList.addItem(pitem)
        else:
            qitem.update(prefix)
        #self.quirkList.sortItems()

    @QtCore.pyqtSlot()
    def addSuffixDialog(self, qitem=None):
        d = {"label": "Value:", "inputname": "value" }
        if qitem is not None:
            d["value"] = qitem.quirk.quirk["value"]
        vdict = MultiTextDialog("ENTER SUFFIX", self, d).getText()
        if vdict is None:
            return
        vdict["type"] = "suffix"
        newquirk = pesterQuirk(vdict)
        if qitem is None:
            item = PesterQuirkItem(newquirk)
            self.quirkList.addItem(item)
        else:
            qitem.update(newquirk)
        #self.quirkList.sortItems()

    @QtCore.pyqtSlot()
    def addSimpleReplaceDialog(self, qitem=None):
        d = [{"label": "Replace:", "inputname": "from"}, {"label": "With:", "inputname": "to"}]
        if qitem is not None:
            d[0]["value"] = qitem.quirk.quirk["from"]
            d[1]["value"] = qitem.quirk.quirk["to"]
        vdict = MultiTextDialog("REPLACE", self, *d).getText()
        if vdict is None:
            return
        vdict["type"] = "replace"
        newquirk = pesterQuirk(vdict)
        if qitem is None:
            item = PesterQuirkItem(newquirk)
            self.quirkList.addItem(item)
        else:
            qitem.update(newquirk)
        #self.quirkList.sortItems()

    @QtCore.pyqtSlot()
    def addRegexpDialog(self, qitem=None):
        d = [{"label": "Regexp:", "inputname": "from"}, {"label": "Replace With:", "inputname": "to"}]
        if qitem is not None:
            d[0]["value"] = qitem.quirk.quirk["from"]
            d[1]["value"] = qitem.quirk.quirk["to"]
        vdict = MultiTextDialog("REGEXP REPLACE", self, *d).getText()
        if vdict is None:
            return
        vdict["type"] = "regexp"
        try:
            re.compile(vdict["from"])
        except re.error, e:
            quirkWarning = QtGui.QMessageBox(self)
            quirkWarning.setText("Not a valid regular expression!")
            quirkWarning.setInformativeText("H3R3S WHY DUMP4SS: %s" % (e))
            quirkWarning.exec_()
            return

        newquirk = pesterQuirk(vdict)
        if qitem is None:
            item = PesterQuirkItem(newquirk)
            self.quirkList.addItem(item)
        else:
            qitem.update(newquirk)
        #self.quirkList.sortItems()
    @QtCore.pyqtSlot()
    def addRandomDialog(self, qitem=None):
        values = {}
        if qitem is not None:
            values["list"] = qitem.quirk.quirk["randomlist"]
            values["regexp"] = qitem.quirk.quirk["from"]
        vdict = RandomQuirkDialog(self, values).getText()
        if vdict is None:
            return
        vdict["type"] = "random"
        try:
            re.compile(vdict["from"])
        except re.error, e:
            quirkWarning = QtGui.QMessageBox(self)
            quirkWarning.setText("Not a valid regular expression!")
            quirkWarning.setInformativeText("H3R3S WHY DUMP4SS: %s" % (e))
            quirkWarning.exec_()
            return
        newquirk = pesterQuirk(vdict)
        if qitem is None:
            item = PesterQuirkItem(newquirk)
            self.quirkList.addItem(item)
        else:
            qitem.update(newquirk)
        #self.quirkList.sortItems()
    @QtCore.pyqtSlot()
    def addSpellDialog(self, qitem=None):
        vdict = MispellQuirkDialog(self).getPercentage()
        if vdict is None:
            return
        vdict["type"] = "spelling"
        newquirk = pesterQuirk(vdict)
        if qitem is None:
            item = PesterQuirkItem(newquirk)
            self.quirkList.addItem(item)
        else:
            qitem.update(newquirk)
        #self.quirkList.sortItems()

class PesterChooseTheme(QtGui.QDialog):
    def __init__(self, config, theme, parent):
        QtGui.QDialog.__init__(self, parent)
        self.config = config
        self.theme = theme
        self.parent = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.setWindowTitle("Pick a theme")

        instructions = QtGui.QLabel("Pick a theme:")

        avail_themes = config.availableThemes()
        self.themeBox = QtGui.QComboBox(self)
        for (i, t) in enumerate(avail_themes):
            self.themeBox.addItem(t)
            if t == theme.name:
                self.themeBox.setCurrentIndex(i)

        self.ok = QtGui.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('accept()'))
        self.cancel = QtGui.QPushButton("CANCEL", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        layout_ok = QtGui.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = QtGui.QVBoxLayout()
        layout_0.addWidget(instructions)
        layout_0.addWidget(self.themeBox)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)

        self.connect(self, QtCore.SIGNAL('accepted()'),
                     parent, QtCore.SLOT('themeSelected()'))
        self.connect(self, QtCore.SIGNAL('rejected()'),
                     parent, QtCore.SLOT('closeTheme()'))

class PesterChooseProfile(QtGui.QDialog):
    def __init__(self, userprofile, config, theme, parent, collision=None):
        QtGui.QDialog.__init__(self, parent)
        self.userprofile = userprofile
        self.theme = theme
        self.config = config
        self.parent = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])

        self.currentHandle = QtGui.QLabel("CHANGING FROM %s" % userprofile.chat.handle)
        self.chumHandle = QtGui.QLineEdit(self)
        self.chumHandle.setMinimumWidth(200)
        self.chumHandleLabel = QtGui.QLabel(self.theme["main/mychumhandle/label/text"], self)
        self.chumColorButton = QtGui.QPushButton(self)
        self.chumColorButton.resize(50, 20)
        self.chumColorButton.setStyleSheet("background: %s" % (userprofile.chat.colorhtml()))
        self.chumcolor = userprofile.chat.color
        self.connect(self.chumColorButton, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('openColorDialog()'))
        layout_1 = QtGui.QHBoxLayout()
        layout_1.addWidget(self.chumHandleLabel)
        layout_1.addWidget(self.chumHandle)
        layout_1.addWidget(self.chumColorButton)

        # available profiles?
        avail_profiles = self.config.availableProfiles()
        if avail_profiles:
            self.profileBox = QtGui.QComboBox(self)
            self.profileBox.addItem("Choose a profile...")
            for p in avail_profiles:
                self.profileBox.addItem(p.chat.handle)
        else:
            self.profileBox = None

        self.defaultcheck = QtGui.QCheckBox(self)
        self.defaultlabel = QtGui.QLabel("Set This Profile As Default", self)
        layout_2 = QtGui.QHBoxLayout()
        layout_2.addWidget(self.defaultlabel)
        layout_2.addWidget(self.defaultcheck)

        self.ok = QtGui.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('validateProfile()'))
        self.cancel = QtGui.QPushButton("CANCEL", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        if not collision and avail_profiles:
            self.delete = QtGui.QPushButton("DELETE", self)
            self.connect(self.delete, QtCore.SIGNAL('clicked()'),
                         self, QtCore.SLOT('deleteProfile()'))
        layout_ok = QtGui.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.ok)

        layout_0 = QtGui.QVBoxLayout()
        if collision:
            collision_warning = QtGui.QLabel("%s is taken already! Pick a new profile." % (collision))
            layout_0.addWidget(collision_warning)
        else:
            layout_0.addWidget(self.currentHandle, alignment=QtCore.Qt.AlignHCenter)
        layout_0.addLayout(layout_1)
        if avail_profiles:
            profileLabel = QtGui.QLabel("Or choose an existing profile:", self)
            layout_0.addWidget(profileLabel)
            layout_0.addWidget(self.profileBox)
        layout_0.addLayout(layout_ok)
        if not collision and avail_profiles:
            layout_0.addWidget(self.delete)
        layout_0.addLayout(layout_2)
        self.errorMsg = QtGui.QLabel(self)
        self.errorMsg.setStyleSheet("color:red;")
        layout_0.addWidget(self.errorMsg)
        self.setLayout(layout_0)

        self.connect(self, QtCore.SIGNAL('accepted()'),
                     parent, QtCore.SLOT('profileSelected()'))
        self.connect(self, QtCore.SIGNAL('rejected()'),
                     parent, QtCore.SLOT('closeProfile()'))

    @QtCore.pyqtSlot()
    def openColorDialog(self):
        self.colorDialog = QtGui.QColorDialog(self)
        color = self.colorDialog.getColor(initial=self.userprofile.chat.color)
        self.chumColorButton.setStyleSheet("background: %s" % color.name())
        self.chumcolor = color
        self.colorDialog = None

    @QtCore.pyqtSlot()
    def validateProfile(self):
        if not self.profileBox or self.profileBox.currentIndex() == 0:
            handle = unicode(self.chumHandle.text())
            if not PesterProfile.checkLength(handle):
                self.errorMsg.setText("PROFILE HANDLE IS TOO LONG")
                return
            if not PesterProfile.checkValid(handle):
                self.errorMsg.setText("NOT A VALID CHUMTAG")
                return
        self.accept()

    @QtCore.pyqtSlot()
    def deleteProfile(self):
        if self.profileBox and self.profileBox.currentIndex() > 0:
            handle = unicode(self.profileBox.currentText())
            if handle == self.parent.profile().handle:
                problem = QtGui.QMessageBox()
                problem.setStyleSheet(self.theme["main/defaultwindow/style"])
                problem.setWindowTitle("Problem!")
                problem.setInformativeText("You can't delete the profile you're currently using!")
                problem.setStandardButtons(QtGui.QMessageBox.Ok)
                problem.exec_()
                return
            msgbox = QtGui.QMessageBox()
            msgbox.setStyleSheet(self.theme["main/defaultwindow/style"])
            msgbox.setWindowTitle("WARNING!")
            msgbox.setInformativeText("Are you sure you want to delete the profile: %s" % (handle))
            msgbox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            ret = msgbox.exec_()
            if ret == QtGui.QMessageBox.Ok:
                try:
                    remove("profiles/%s.js" % (handle))
                except OSError:
                    problem = QtGui.QMessageBox()
                    problem.setStyleSheet(self.theme["main/defaultwindow/style"])
                    problem.setWindowTitle("Problem!")
                    problem.setInformativeText("There was a problem deleting the profile: %s" % (handle))
                    problem.setStandardButtons(QtGui.QMessageBox.Ok)
                    problem.exec_()

class PesterOptions(QtGui.QDialog):
    def __init__(self, config, theme, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle("Options")
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.setStyleSheet(self.theme["main/defaultwindow/style"])

        layout_4 = QtGui.QVBoxLayout()

        hr = QtGui.QFrame()
        hr.setFrameShape(QtGui.QFrame.HLine)
        hr.setFrameShadow(QtGui.QFrame.Sunken)
        vr = QtGui.QFrame()
        vr.setFrameShape(QtGui.QFrame.VLine)
        vr.setFrameShadow(QtGui.QFrame.Sunken)

        self.tabs = QtGui.QButtonGroup(self)
        self.connect(self.tabs, QtCore.SIGNAL('buttonClicked(int)'),
                     self, QtCore.SLOT('changePage(int)'))
        tabNames = ["Chum List", "Conversations", "Interface", "Sound", "Logging", "Idle", "Theme"]
        if parent.advanced: tabNames.append("Advanced")
        for t in tabNames:
            button = QtGui.QPushButton(t)
            self.tabs.addButton(button)
            layout_4.addWidget(button)
            button.setCheckable(True)
        self.tabs.button(-2).setChecked(True)
        self.pages = QtGui.QStackedWidget(self)

        self.tabcheck = QtGui.QCheckBox("Tabbed Conversations", self)
        if self.config.tabs():
            self.tabcheck.setChecked(True)
        self.hideOffline = QtGui.QCheckBox("Hide Offline Chums", self)
        if self.config.hideOfflineChums():
            self.hideOffline.setChecked(True)

        self.soundcheck = QtGui.QCheckBox("Sounds On", self)
        self.connect(self.soundcheck, QtCore.SIGNAL('stateChanged(int)'),
                     self, QtCore.SLOT('soundChange(int)'))
        self.chatsoundcheck = QtGui.QCheckBox("Pester Sounds", self)
        self.chatsoundcheck.setChecked(self.config.chatSound())
        self.memosoundcheck = QtGui.QCheckBox("Memo Sounds", self)
        self.memosoundcheck.setChecked(self.config.memoSound())
        if self.config.soundOn():
            self.soundcheck.setChecked(True)
        else:
            self.chatsoundcheck.setEnabled(False)
            self.memosoundcheck.setEnabled(False)


        self.timestampcheck = QtGui.QCheckBox("Time Stamps", self)
        if self.config.showTimeStamps():
            self.timestampcheck.setChecked(True)

        self.timestampBox = QtGui.QComboBox(self)
        self.timestampBox.addItem("12 hour")
        self.timestampBox.addItem("24 hour")
        if self.config.time12Format():
            self.timestampBox.setCurrentIndex(0)
        else:
            self.timestampBox.setCurrentIndex(1)
        self.secondscheck = QtGui.QCheckBox("Show Seconds", self)
        if self.config.showSeconds():
            self.secondscheck.setChecked(True)

        self.memomessagecheck = QtGui.QCheckBox("Show OP and Voice Messages in Memos", self)
        if self.config.opvoiceMessages():
            self.memomessagecheck.setChecked(True)

        self.animationscheck = QtGui.QCheckBox("Use animated smilies", self)
        if self.config.animations():
            self.animationscheck.setChecked(True)
        animateLabel = QtGui.QLabel("(Disable if you leave chats open for LOOOONG periods of time)")
        font = animateLabel.font()
        font.setPointSize(8)
        animateLabel.setFont(font)

        self.userlinkscheck = QtGui.QCheckBox("Disable #Memo and @User Links", self)
        self.userlinkscheck.setChecked(self.config.disableUserLinks())
        self.userlinkscheck.setVisible(False)


        # Will add ability to turn off groups later
        #self.groupscheck = QtGui.QCheckBox("Use Groups", self)
        #self.groupscheck.setChecked(self.config.useGroups())
        self.showemptycheck = QtGui.QCheckBox("Show Empty Groups", self)
        self.showemptycheck.setChecked(self.config.showEmptyGroups())
        self.showonlinenumbers = QtGui.QCheckBox("Show Number of Online Chums", self)
        self.showonlinenumbers.setChecked(self.config.showOnlineNumbers())

        sortLabel = QtGui.QLabel("Sort Chums")
        self.sortBox = QtGui.QComboBox(self)
        self.sortBox.addItem("Alphabetically")
        self.sortBox.addItem("By Mood")
        method = self.config.sortMethod()
        if method >= 0 and method < self.sortBox.count():
            self.sortBox.setCurrentIndex(method)
        layout_3 = QtGui.QHBoxLayout()
        layout_3.addWidget(sortLabel)
        layout_3.addWidget(self.sortBox, 10)

        self.logpesterscheck = QtGui.QCheckBox("Log all Pesters", self)
        if self.config.logPesters() & self.config.LOG:
            self.logpesterscheck.setChecked(True)
        self.logmemoscheck = QtGui.QCheckBox("Log all Memos", self)
        if self.config.logMemos() & self.config.LOG:
            self.logmemoscheck.setChecked(True)
        self.stamppestercheck = QtGui.QCheckBox("Log Time Stamps for Pesters", self)
        if self.config.logPesters() & self.config.STAMP:
            self.stamppestercheck.setChecked(True)
        self.stampmemocheck = QtGui.QCheckBox("Log Time Stamps for Memos", self)
        if self.config.logMemos() & self.config.STAMP:
            self.stampmemocheck.setChecked(True)

        self.idleBox = QtGui.QSpinBox(self)
        self.idleBox.setStyleSheet("background:#FFFFFF")
        self.idleBox.setRange(1, 1440)
        self.idleBox.setValue(self.config.idleTime())
        layout_5 = QtGui.QHBoxLayout()
        layout_5.addWidget(QtGui.QLabel("Minutes before Idle:"))
        layout_5.addWidget(self.idleBox)

        avail_themes = self.config.availableThemes()
        self.themeBox = QtGui.QComboBox(self)
        for (i, t) in enumerate(avail_themes):
            self.themeBox.addItem(t)
            if t == theme.name:
                self.themeBox.setCurrentIndex(i)

        self.buttonOptions = ["Minimize to Taskbar", "Minimize to Tray", "Quit"]
        self.miniBox = QtGui.QComboBox(self)
        self.miniBox.addItems(self.buttonOptions)
        self.miniBox.setCurrentIndex(self.config.minimizeAction())
        self.closeBox = QtGui.QComboBox(self)
        self.closeBox.addItems(self.buttonOptions)
        self.closeBox.setCurrentIndex(self.config.closeAction())
        layout_mini = QtGui.QHBoxLayout()
        layout_mini.addWidget(QtGui.QLabel("Minimize"))
        layout_mini.addWidget(self.miniBox)
        layout_close = QtGui.QHBoxLayout()
        layout_close.addWidget(QtGui.QLabel("Close"))
        layout_close.addWidget(self.closeBox)

        if parent.advanced:
            self.modechange = QtGui.QLineEdit(self)
            layout_change = QtGui.QHBoxLayout()
            layout_change.addWidget(QtGui.QLabel("Change:"))
            layout_change.addWidget(self.modechange)

        self.ok = QtGui.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('accept()'))
        self.cancel = QtGui.QPushButton("CANCEL", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        layout_2 = QtGui.QHBoxLayout()
        layout_2.addWidget(self.cancel)
        layout_2.addWidget(self.ok)

        # Tab layouts
        # Chum List
        widget = QtGui.QWidget()
        layout_chumlist = QtGui.QVBoxLayout(widget)
        layout_chumlist.setAlignment(QtCore.Qt.AlignTop)
        layout_chumlist.addWidget(self.hideOffline)
        #layout_chumlist.addWidget(self.groupscheck)
        layout_chumlist.addWidget(self.showemptycheck)
        layout_chumlist.addWidget(self.showonlinenumbers)
        layout_chumlist.addLayout(layout_3)
        self.pages.addWidget(widget)

        # Conversations
        widget = QtGui.QWidget()
        layout_chat = QtGui.QVBoxLayout(widget)
        layout_chat.setAlignment(QtCore.Qt.AlignTop)
        layout_chat.addWidget(self.timestampcheck)
        layout_chat.addWidget(self.timestampBox)
        layout_chat.addWidget(self.secondscheck)
        layout_chat.addWidget(self.memomessagecheck)
        layout_chat.addWidget(self.animationscheck)
        layout_chat.addWidget(animateLabel)
        # Re-enable these when it's possible to disable User and Memo links
        #layout_chat.addWidget(hr)
        #layout_chat.addWidget(QtGui.QLabel("User and Memo Links"))
        #layout_chat.addWidget(self.userlinkscheck)
        self.pages.addWidget(widget)

        # Interface
        widget = QtGui.QWidget()
        layout_interface = QtGui.QVBoxLayout(widget)
        layout_interface.setAlignment(QtCore.Qt.AlignTop)
        layout_interface.addWidget(self.tabcheck)
        layout_interface.addLayout(layout_mini)
        layout_interface.addLayout(layout_close)
        self.pages.addWidget(widget)

        # Sound
        widget = QtGui.QWidget()
        layout_sound = QtGui.QVBoxLayout(widget)
        layout_sound.setAlignment(QtCore.Qt.AlignTop)
        layout_sound.addWidget(self.soundcheck)
        layout_indent = QtGui.QVBoxLayout()
        layout_indent.addWidget(self.chatsoundcheck)
        layout_indent.addWidget(self.memosoundcheck)
        layout_indent.setContentsMargins(22,0,0,0)
        layout_sound.addLayout(layout_indent)
        self.pages.addWidget(widget)

        # Logging
        widget = QtGui.QWidget()
        layout_logs = QtGui.QVBoxLayout(widget)
        layout_logs.setAlignment(QtCore.Qt.AlignTop)
        layout_logs.addWidget(self.logpesterscheck)
        layout_logs.addWidget(self.logmemoscheck)
        layout_logs.addWidget(self.stamppestercheck)
        layout_logs.addWidget(self.stampmemocheck)
        self.pages.addWidget(widget)

        # Idle
        widget = QtGui.QWidget()
        layout_idle = QtGui.QVBoxLayout(widget)
        layout_idle.setAlignment(QtCore.Qt.AlignTop)
        layout_idle.addLayout(layout_5)
        self.pages.addWidget(widget)

        # Theme
        widget = QtGui.QWidget()
        layout_theme = QtGui.QVBoxLayout(widget)
        layout_theme.setAlignment(QtCore.Qt.AlignTop)
        layout_theme.addWidget(QtGui.QLabel("Pick a Theme:"))
        layout_theme.addWidget(self.themeBox)
        self.pages.addWidget(widget)

        # Advanced
        if parent.advanced:
            widget = QtGui.QWidget()
            layout_advanced = QtGui.QVBoxLayout(widget)
            layout_advanced.setAlignment(QtCore.Qt.AlignTop)
            layout_advanced.addWidget(QtGui.QLabel("Current User Mode: %s" % parent.modes))
            layout_advanced.addLayout(layout_change)
            self.pages.addWidget(widget)

        layout_0 = QtGui.QVBoxLayout()
        layout_1 = QtGui.QHBoxLayout()
        layout_1.addLayout(layout_4)
        layout_1.addWidget(vr)
        layout_1.addWidget(self.pages)
        layout_0.addLayout(layout_1)
        layout_0.addSpacing(30)
        layout_0.addLayout(layout_2)

        self.setLayout(layout_0)

    @QtCore.pyqtSlot(int)
    def changePage(self, page):
        self.tabs.button(page).setChecked(True)
        # What is this, I don't even. qt, fuck
        page = -page - 2
        self.pages.setCurrentIndex(page)
    @QtCore.pyqtSlot(int)
    def soundChange(self, state):
        if state == 0:
            self.chatsoundcheck.setEnabled(False)
            self.memosoundcheck.setEnabled(False)
        else:
            self.chatsoundcheck.setEnabled(True)
            self.memosoundcheck.setEnabled(True)

class PesterUserlist(QtGui.QDialog):
    def __init__(self, config, theme, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setModal(False)
        self.config = config
        self.theme = theme
        self.mainwindow = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.resize(200, 600)

        self.label = QtGui.QLabel("USERLIST")
        self.userarea = RightClickList(self)
        self.userarea.setStyleSheet(self.theme["main/chums/style"])
        self.userarea.optionsMenu = QtGui.QMenu(self)

        self.addChumAction = QtGui.QAction(self.mainwindow.theme["main/menus/rclickchumlist/addchum"], self)
        self.connect(self.addChumAction, QtCore.SIGNAL('triggered()'),
                     self, QtCore.SLOT('addChumSlot()'))
        self.pesterChumAction = QtGui.QAction(self.mainwindow.theme["main/menus/rclickchumlist/pester"], self)
        self.connect(self.pesterChumAction, QtCore.SIGNAL('triggered()'),
                     self, QtCore.SLOT('pesterChumSlot()'))
        self.userarea.optionsMenu.addAction(self.addChumAction)
        self.userarea.optionsMenu.addAction(self.pesterChumAction)

        self.ok = QtGui.QPushButton("OK", self)
        self.ok.setDefault(True)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('accept()'))

        layout_0 = QtGui.QVBoxLayout()
        layout_0.addWidget(self.label)
        layout_0.addWidget(self.userarea)
        layout_0.addWidget(self.ok)

        self.setLayout(layout_0)

        self.connect(self.mainwindow, QtCore.SIGNAL('namesUpdated()'),
                     self, QtCore.SLOT('updateUsers()'))

        self.connect(self.mainwindow,
                     QtCore.SIGNAL('userPresentSignal(QString, QString, QString)'),
                     self,
                     QtCore.SLOT('updateUserPresent(QString, QString, QString)'))
        self.updateUsers()
    @QtCore.pyqtSlot()
    def updateUsers(self):
        names = self.mainwindow.namesdb["#pesterchum"]
        self.userarea.clear()
        for n in names:
            item = QtGui.QListWidgetItem(n)
            item.setTextColor(QtGui.QColor(self.theme["main/chums/userlistcolor"]))
            self.userarea.addItem(item)
        self.userarea.sortItems()
    @QtCore.pyqtSlot(QtCore.QString, QtCore.QString, QtCore.QString)
    def updateUserPresent(self, handle, channel, update):
        h = unicode(handle)
        c = unicode(channel)
        if update == "quit":
            self.delUser(h)
        elif update == "left" and c == "#pesterchum":
            self.delUser(h)
        elif update == "join" and c == "#pesterchum":
            self.addUser(h)
    def addUser(self, name):
        item = QtGui.QListWidgetItem(name)
        item.setTextColor(QtGui.QColor(self.theme["main/chums/userlistcolor"]))
        self.userarea.addItem(item)
        self.userarea.sortItems()
    def delUser(self, name):
        matches = self.userarea.findItems(name, QtCore.Qt.MatchFlags(0))
        for m in matches:
            self.userarea.takeItem(self.userarea.row(m))

    def changeTheme(self, theme):
        self.theme = theme
        self.setStyleSheet(theme["main/defaultwindow/style"])
        self.userarea.setStyleSheet(theme["main/chums/style"])
        self.addChumAction.setText(theme["main/menus/rclickchumlist/addchum"])
        for item in [self.userarea.item(i) for i in range(0, self.userarea.count())]:
            item.setTextColor(QtGui.QColor(theme["main/chums/userlistcolor"]))

    @QtCore.pyqtSlot()
    def addChumSlot(self):
        cur = self.userarea.currentItem()
        if not cur:
            return
        self.addChum.emit(cur.text())
    @QtCore.pyqtSlot()
    def pesterChumSlot(self):
        cur = self.userarea.currentItem()
        if not cur:
            return
        self.pesterChum.emit(cur.text())

    addChum = QtCore.pyqtSignal(QtCore.QString)
    pesterChum = QtCore.pyqtSignal(QtCore.QString)


class MemoListItem(QtGui.QTreeWidgetItem):
    def __init__(self, channel, usercount):
        QtGui.QTreeWidgetItem.__init__(self, [channel, str(usercount)])
        self.target = channel

class PesterMemoList(QtGui.QDialog):
    def __init__(self, parent, channel=""):
        QtGui.QDialog.__init__(self, parent)
        self.setModal(False)
        self.theme = parent.theme
        self.mainwindow = parent
        self.setStyleSheet(self.theme["main/defaultwindow/style"])
        self.resize(460, 300)

        self.label = QtGui.QLabel("MEMOS")
        self.channelarea = RightClickTree(self)
        self.channelarea.setStyleSheet(self.theme["main/chums/style"])
        self.channelarea.optionsMenu = QtGui.QMenu(self)
        self.channelarea.setColumnCount(2)
        self.channelarea.setHeaderLabels(["Memo", "Users"])
        self.channelarea.setIndentation(0)
        self.channelarea.setColumnWidth(0,200)
        self.channelarea.setColumnWidth(1,10)
        self.connect(self.channelarea,
                     QtCore.SIGNAL('itemActivated(QTreeWidgetItem *, int)'),
                     self, QtCore.SLOT('joinActivatedMemo(QTreeWidgetItem, int)'))

        self.orjoinlabel = QtGui.QLabel("OR MAKE A NEW MEMO:")
        self.newmemo = QtGui.QLineEdit(channel, self)
        self.secretChannel = QtGui.QCheckBox("HIDDEN CHANNEL?", self)
        self.inviteChannel = QtGui.QCheckBox("INVITATION ONLY?", self)

        self.timelabel = QtGui.QLabel("TIMEFRAME:")
        self.timeslider = TimeSlider(QtCore.Qt.Horizontal, self)
        self.timeinput = TimeInput(self.timeslider, self)

        self.cancel = QtGui.QPushButton("CANCEL", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        self.join = QtGui.QPushButton("JOIN", self)
        self.join.setDefault(True)
        self.connect(self.join, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('checkEmpty()'))
        layout_ok = QtGui.QHBoxLayout()
        layout_ok.addWidget(self.cancel)
        layout_ok.addWidget(self.join)

        layout_left  = QtGui.QVBoxLayout()
        layout_right = QtGui.QVBoxLayout()
        layout_right.setAlignment(QtCore.Qt.AlignTop)
        layout_0 = QtGui.QVBoxLayout()
        layout_1 = QtGui.QHBoxLayout()
        layout_left.addWidget(self.label)
        layout_left.addWidget(self.channelarea)
        layout_right.addWidget(self.orjoinlabel)
        layout_right.addWidget(self.newmemo)
        layout_right.addWidget(self.secretChannel)
        layout_right.addWidget(self.inviteChannel)
        layout_right.addWidget(self.timelabel)
        layout_right.addWidget(self.timeslider)
        layout_right.addWidget(self.timeinput)
        layout_1.addLayout(layout_left)
        layout_1.addLayout(layout_right)
        layout_0.addLayout(layout_1)
        layout_0.addLayout(layout_ok)

        self.setLayout(layout_0)

    def newmemoname(self):
        return self.newmemo.text()
    def selectedmemo(self):
        return self.channelarea.currentItem()

    def updateChannels(self, channels):
        for c in channels:
            item = MemoListItem(c[0][1:],c[1])
            item.setTextColor(0, QtGui.QColor(self.theme["main/chums/userlistcolor"]))
            item.setTextColor(1, QtGui.QColor(self.theme["main/chums/userlistcolor"]))
            item.setIcon(0, QtGui.QIcon(self.theme["memos/memoicon"]))
            self.channelarea.addTopLevelItem(item)

    def updateTheme(self, theme):
        self.theme = theme
        self.setStyleSheet(theme["main/defaultwindow/style"])
        for item in [self.userarea.item(i) for i in range(0, self.channelarea.count())]:
            item.setTextColor(QtGui.QColor(theme["main/chums/userlistcolor"]))
            item.setIcon(QtGui.QIcon(theme["memos/memoicon"]))

    @QtCore.pyqtSlot()
    def checkEmpty(self):
        newmemo = self.newmemoname()
        selectedmemo = self.selectedmemo()
        if newmemo or selectedmemo:
            self.accept()
    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
    def joinActivatedMemo(self, item, column):
        self.channelarea.setCurrentItem(item, column)
        self.accept()


class LoadingScreen(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent, (QtCore.Qt.CustomizeWindowHint |
                                              QtCore.Qt.FramelessWindowHint))
        self.mainwindow = parent
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])

        self.loadinglabel = QtGui.QLabel("CONN3CT1NG", self)
        self.cancel = QtGui.QPushButton("QU1T >:?", self)
        self.ok = QtGui.QPushButton("R3CONN3CT >:]", self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SIGNAL('tryAgain()'))

        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.loadinglabel)
        layout_1 = QtGui.QHBoxLayout()
        layout_1.addWidget(self.cancel)
        layout_1.addWidget(self.ok)
        self.layout.addLayout(layout_1)
        self.setLayout(self.layout)

    def hideReconnect(self):
        self.ok.hide()
    def showReconnect(self):
        self.ok.show()

    tryAgain = QtCore.pyqtSignal()

class AboutPesterchum(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.mainwindow = parent
        self.setStyleSheet(self.mainwindow.theme["main/defaultwindow/style"])

        self.title = QtGui.QLabel("P3ST3RCHUM V. %s" % (_pcVersion))
        self.credits = QtGui.QLabel("Programming by:\n\
  illuminatedwax (ghostDunk)\n\
  Kiooeht (evacipatedBox)\n\
  alGore\n\
\n\
Art by:\n\
  Grimlive (aquaMarinist)\n\
  binaryCabalist\n\
\n\
Special Thanks:\n\
  ABT\n\
  gamblingGenocider")

        self.ok = QtGui.QPushButton("OK", self)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'),
                     self, QtCore.SLOT('reject()'))

        layout_0 = QtGui.QVBoxLayout()
        layout_0.addWidget(self.title)
        layout_0.addWidget(self.credits)
        layout_0.addWidget(self.ok)

        self.setLayout(layout_0)
