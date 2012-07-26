# cvl.py
"""
A wxPython GUI to provide an easy way to launch a CVL instance, 
initially on Mac OS X.  It can be run using "python cvl.py",
assuming that you have a 32-bit version of Python installed,
wxPython, and the dependent Python modules imported below.

The py2app module is required to build the CVL Administrator.app 
application bundle, which can be built as follows:

   python create_cvlAdministrator_bundle.py py2app
  
"""

# Later, STDERR will be redirected to logTextCtrl
# For now, we just want make sure that the Launcher doesn't attempt 
# to write to CVL Administrator.exe.log, because it might not have
# permission to do so.
import sys
sys.stderr = sys.stdout

if sys.platform.startswith("win"):
    import _winreg
import subprocess
import wx
import time
import traceback
import threading
import os
import ssh # Pure Python-based ssh module, based on Paramiko, published on PyPi
#import libssh2 # Unpublished SSH module (Python bindings for libssh2) by Sebastian Noack: git clone git://github.com/wallunit/ssh4py
import HTMLParser
import urllib
import cvl_administrator_version_number
import StringIO
import xmlrpclib
import appdirs
import ConfigParser
import boto
from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
#import logging

#logger = ssh.util.logging.getLogger()
#logger.setLevel(logging.WARN)

defaultImageName = ""
global imageName
imageName = ""
defaultInstanceName = "CVL Instance 1"
instanceName = defaultInstanceName
global sshKeyPair
sshKeyPair = ""
global securityGroup
securityGroup = "default"
global contactEmail
contactEmail = ""
global sshTunnelProcess
sshTunnelProcess = None
global sshTunnelReady
sshTunnelReady = False
global localPortNumber
localPortNumber = "5901"
global privateKeyFile
global launchDialogFrame
launchDialogFrame = None

global ec2CredentialsZipFilePath
ec2CredentialsZipFilePath = ""
global ec2Connection
ec2Connection = None

class MyHtmlParser(HTMLParser.HTMLParser):
  def __init__(self):
    HTMLParser.HTMLParser.__init__(self)
    self.recording = 0
    self.data = []

  def handle_starttag(self, tag, attributes):
    if tag != 'span':
      return
    if self.recording:
      self.recording += 1
      return
    for name, value in attributes:
      if name == 'id' and value == 'CVLAdministratorLatestVersionNumber':
        break
    else:
      return
    self.recording = 1

  def handle_endtag(self, tag):
    if tag == 'span' and self.recording:
      self.recording -= 1

  def handle_data(self, data):
    if self.recording:
      self.data.append(data)

class MyFrame(wx.Frame):

    def __init__(self, parent, id, title):

        global logTextCtrl

        # The default window style is wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.CLIP_CHILDREN
        # If you remove wx.RESIZE_BORDER from it, you'll get a frame which cannot be resized.
        # wx.Frame(parent, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        if sys.platform.startswith("darwin"):
            wx.Frame.__init__(self, parent, id, title, size=(400, 390), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        else:
            wx.Frame.__init__(self, parent, id, title, size=(400, 430), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('CVL Administrator.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import cvlAdministratorIcon
            self.SetIcon(cvlAdministratorIcon.getMASSIVElogoTransparent128x128Icon())

        self.menu_bar  = wx.MenuBar()

        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.file_menu = wx.Menu()
            self.file_menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
            self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
            self.menu_bar.Append(self.file_menu, "&File")

        if sys.platform.startswith("darwin"):
            # Only do this for Mac OS X, because other platforms have
            # a right-click pop-up menu for wx.TextCtrl with Copy,
            # Select All etc. Plus, the menu doesn't look that good on
            # the CVL Administrator main dialog, and doesn't work for
            # non Mac platforms, because of FindFocus() will always
            # find the window/dialog which contains the menu.
            self.edit_menu = wx.Menu()
            self.edit_menu.Append(wx.ID_CUT, "Cut", "Cut the selected text")
            self.Bind(wx.EVT_MENU, self.OnCut, id=wx.ID_CUT)
            self.edit_menu.Append(wx.ID_COPY, "Copy", "Copy the selected text")
            self.Bind(wx.EVT_MENU, self.OnCopy, id=wx.ID_COPY)
            self.edit_menu.Append(wx.ID_PASTE, "Paste", "Paste text from the clipboard")
            self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
            self.edit_menu.Append(wx.ID_SELECTALL, "Select All")
            self.Bind(wx.EVT_MENU, self.OnSelectAll, id=wx.ID_SELECTALL)
            self.menu_bar.Append(self.edit_menu, "&Edit")

        self.help_menu = wx.Menu()
        self.help_menu.Append(wx.ID_ABOUT,   "&About CVL Administrator")
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetTitle("CVL Administrator")

        self.SetMenuBar(self.menu_bar)

        # Let's implement the About menu using py2app instead,
        # so that we can easily insert the version number.
        # We may need to treat different OS's differently.

        global launchDialogPanel
        launchDialogPanel = wx.Panel(self)

        global cvlImageNameLabel
        cvlImageNameLabel = wx.StaticText(launchDialogPanel, -1, 'Image name', (10, 60))
        global cvlInstanceNameLabel
        cvlInstanceNameLabel = wx.StaticText(launchDialogPanel, -1, 'Instance name', (10, 100))
        global cvlAdministratorSshKeyPairLabel
        cvlAdministratorSshKeyPairLabel = wx.StaticText(launchDialogPanel, -1, 'SSH key pair', (10, 140))
        global cvlAdministratorSecurityGroupLabel
        cvlAdministratorSecurityGroupLabel = wx.StaticText(launchDialogPanel, -1, 'Security group', (10, 180))
        global cvlAdministratorContactEmailLabel
        cvlAdministratorContactEmailLabel = wx.StaticText(launchDialogPanel, -1, 'Contact email', (10, 220))

        widgetWidth1 = 220
        widgetWidth2 = 220
        if not sys.platform.startswith("win"):
            widgetWidth2 = widgetWidth2 + 25

        global defaultImageName
        defaultImageName = "Centos 6.2 amd64"

        images = ec2Connection.get_all_images()
        imageNames = []
        for image in images:
            imageNames.append(image.name)

        global imageNameComboBox
        imageNameComboBox = wx.ComboBox(launchDialogPanel, -1, value='', pos=(125, 55), size=(widgetWidth2, -1),choices=imageNames, style=wx.CB_DROPDOWN)
        if config.has_section("CVL Administrator Preferences"):
            if config.has_option("CVL Administrator Preferences", "imageName"):
                imageName = config.get("CVL Administrator Preferences", "imageName")
            else:
                config.set("CVL Administrator Preferences","imageName","")
                with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                    config.write(cvlAdministratorPreferencesFileObject)
        else:
            config.add_section("CVL Administrator Preferences")
            with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                config.write(cvlAdministratorPreferencesFileObject)
        if imageName.strip()!="":
            imageNameComboBox.SetValue(imageName)
        else:
            imageNameComboBox.SetValue(defaultImageName)

        global instanceNameTextField
        if sys.platform.startswith("darwin"):
            instanceNameTextField = wx.TextCtrl(launchDialogPanel, -1, value=defaultInstanceName, pos=(127, 95), size=(widgetWidth1, -1))
        else:
            instanceNameTextField = wx.TextCtrl(launchDialogPanel, -1, value=defaultInstanceName, pos=(125, 95), size=(widgetWidth1, -1))
        if instanceName.strip()!="":
            instanceNameTextField.SelectAll()
        instanceNameTextField.SetFocus()

        global defaultSshKeyPair
        defaultSshKeyPair = ""

        ssh_key_pairs = ec2Connection.get_all_key_pairs()
        sshKeyPairs = []
        for ssh_key_pair in ssh_key_pairs:
            sshKeyPairs.append(ssh_key_pair.name)

        if len(sshKeyPairs) > 0:
            sshKeyPair = sshKeyPairs[0]

        global sshKeyPairComboBox
        sshKeyPairComboBox = wx.ComboBox(launchDialogPanel, -1, value='', pos=(125, 135), size=(widgetWidth2, -1),choices=sshKeyPairs, style=wx.CB_DROPDOWN)
        if config.has_section("CVL Administrator Preferences"):
            if config.has_option("CVL Administrator Preferences", "sshKeyPair"):
                sshKeyPair = config.get("CVL Administrator Preferences", "sshKeyPair")
            else:
                config.set("CVL Administrator Preferences","sshKeyPair","")
                with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                    config.write(cvlAdministratorPreferencesFileObject)
        else:
            config.add_section("CVL Administrator Preferences")
            with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                config.write(cvlAdministratorPreferencesFileObject)
        if sshKeyPair.strip()!="":
            sshKeyPairComboBox.SetValue(sshKeyPair)
        else:
            sshKeyPairComboBox.SetValue(defaultSshKeyPair)

        defaultSecurityGroup = "default"
        securityGroup = defaultSecurityGroup

        security_groups = ec2Connection.get_all_security_groups()
        securityGroups = []
        for security_group in security_groups:
            securityGroups.append(security_group.name)

        global securityGroupComboBox
        securityGroupComboBox = wx.ComboBox(launchDialogPanel, -1, value='', pos=(125, 175), size=(widgetWidth2, -1),choices=securityGroups, style=wx.CB_DROPDOWN)
        if config.has_section("CVL Administrator Preferences"):
            if config.has_option("CVL Administrator Preferences", "securityGroup"):
                securityGroup = config.get("CVL Administrator Preferences", "securityGroup")
            else:
                config.set("CVL Administrator Preferences","securityGroup","")
                with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                    config.write(cvlAdministratorPreferencesFileObject)
        else:
            config.add_section("CVL Administrator Preferences")
            with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                config.write(cvlAdministratorPreferencesFileObject)
        if securityGroup.strip()!="":
            securityGroupComboBox.SetValue(securityGroup)
        else:
            securityGroupComboBox.SetValue(defaultSecurityGroup)

        global contactEmail
        if config.has_section("CVL Administrator Preferences"):
            if config.has_option("CVL Administrator Preferences", "contactEmail"):
                contactEmail = config.get("CVL Administrator Preferences", "contactEmail")
            else:
                config.set("CVL Administrator Preferences","contactEmail","")
                with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                    config.write(cvlAdministratorPreferencesFileObject)
        else:
            config.add_section("CVL Administrator Preferences")
            with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
                config.write(cvlAdministratorPreferencesFileObject)
        global contactEmailTextField
        if sys.platform.startswith("darwin"):
            contactEmailTextField = wx.TextCtrl(launchDialogPanel, -1, contactEmail,  (127, 215), (widgetWidth1, -1))
        else:
            contactEmailTextField = wx.TextCtrl(launchDialogPanel, -1, contactEmail,  (125, 215), (widgetWidth1, -1))

        instanceNameTextField.MoveAfterInTabOrder(imageNameComboBox)
        sshKeyPairComboBox.MoveAfterInTabOrder(instanceNameTextField)
        securityGroupComboBox.MoveAfterInTabOrder(sshKeyPairComboBox)
        contactEmailTextField.MoveAfterInTabOrder(securityGroupComboBox)

        global cancelButton
        cancelButton = wx.Button(launchDialogPanel, 1, 'Cancel', (130, 305))
        global loginButton
        loginButton = wx.Button(launchDialogPanel, 2, 'Launch', (230, 305))
        loginButton.SetDefault()

        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=1)
        self.Bind(wx.EVT_BUTTON, self.OnLaunch, id=2)

        self.statusbar = MyStatusBar(self)
        global launchDialogStatusBar
        launchDialogStatusBar = self.statusbar
        self.SetStatusBar(self.statusbar)
        self.Centre()

    def OnAbout(self, event):
        dlg = wx.MessageDialog(self, "Version " + cvl_administrator_version_number.version_number + "\n",
                                "CVL Administrator", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self, event):
        try:
            os.unlink(privateKeyFile.name)
        finally:
            os._exit(0)

    def OnCancel(self, event):
        try:
            os.unlink(privateKeyFile.name)
        finally:
            os._exit(0)

    def OnCut(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Cut()

    def OnCopy(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Copy()

    def OnPaste(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Paste()

    def OnSelectAll(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.SelectAll()

    def OnLaunch(self, event):
        class LaunchThread(threading.Thread):
            """Launch Thread Class."""
            def __init__(self, notify_window):
                """Init Worker Thread Class."""
                threading.Thread.__init__(self)
                self._notify_window = notify_window
                self._want_abort = 0
                # This starts the thread running on creation, but you could
                # also make the GUI thread responsible for calling this
                self.start()

            def run(self):
                """Run Worker Thread."""
                # This is the time-consuming code executing in the new thread. 

                waitCursor = wx.StockCursor(wx.CURSOR_WAIT)
                launchDialogFrame.SetCursor(waitCursor)
                launchDialogPanel.SetCursor(waitCursor)
                cvlInstanceNameLabel.SetCursor(waitCursor)
                cvlAdministratorContactEmailLabel.SetCursor(waitCursor)
                instanceNameTextField.SetCursor(waitCursor)
                contactEmailTextField.SetCursor(waitCursor)
                cancelButton.SetCursor(waitCursor)
                loginButton.SetCursor(waitCursor)

                global logTextCtrl
                global launchDialogStatusBar

                try:
                    wx.CallAfter(launchDialogStatusBar.SetStatusText, "Launching " + instanceName + "...")
                    wx.CallAfter(sys.stdout.write, "Launching " + instanceName + "...\n")
                    

                    # ...

                except:
                    wx.CallAfter(sys.stdout.write, "CVL Administrator v" + cvl_administrator_version_number.version_number + "\n")
                    wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                    launchDialogFrame.SetCursor(arrowCursor)
                    launchDialogPanel.SetCursor(arrowCursor)
                    cvlInstanceNameLabel.SetCursor(arrowCursor)
                    cvlAdministratorContactEmailLabel.SetCursor(arrowCursor)
                    instanceNameTextField.SetCursor(arrowCursor)
                    contactEmailTextField.SetCursor(arrowCursor)
                    cancelButton.SetCursor(arrowCursor)
                    loginButton.SetCursor(arrowCursor)

            def abort(self):
                """abort worker thread."""
                # Method for use by main thread to signal an abort
                self._want_abort = 1

        imageName = imageNameComboBox.GetValue()
        instanceName = instanceNameTextField.GetValue()
        sshKeyPair = sshKeyPairComboBox.GetValue()
        securityGroup = securityGroupComboBox.GetValue()
        contactEmail = contactEmailTextField.GetValue()

        config.set("CVL Administrator Preferences","imageName",imageName)
        config.set("CVL Administrator Preferences","sshKeyPair",sshKeyPair)
        config.set("CVL Administrator Preferences","securityGroup",securityGroup)
        config.set("CVL Administrator Preferences","contactEmail",contactEmail)
        with open(cvlAdministratorPreferencesFilePath, 'wb') as cvlAdministratorPreferencesFileObject:
            config.write(cvlAdministratorPreferencesFileObject)

        logWindow = wx.Frame(self, title="Launching a Characterisation Virtual Laboratory Instance", name="CVL Launch Instance",pos=(200,150),size=(700,450))

        if sys.platform.startswith("win"):
            _icon = wx.Icon('CVL Administrator.ico', wx.BITMAP_TYPE_ICO)
            logWindow.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import cvlAdministratorIcon
            logWindow.SetIcon(cvlAdministratorIcon.getMASSIVElogoTransparent128x128Icon())

        logTextCtrl = wx.TextCtrl(logWindow, style=wx.TE_MULTILINE|wx.TE_READONLY)
        gs = wx.GridSizer(rows=1, cols=1, vgap=5, hgap=5)
        gs.Add(logTextCtrl, 0, wx.EXPAND)
        logWindow.SetSizer(gs)
        if sys.platform.startswith("darwin"):
            font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        else:
            font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        logTextCtrl.SetFont(font)
        logWindow.Show(True)

        sys.stdout = logTextCtrl
        sys.stderr = logTextCtrl

        LaunchThread(self)

class MyStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent)

        self.SetFieldsCount(2)
        self.SetStatusText('Welcome to the Characterisation Virtual Laboratory', 0)
        self.SetStatusWidths([-5, -2])

class MyApp(wx.App):
    def OnInit(self):

        appDirs = appdirs.AppDirs("CVL Administrator", "Monash University")
        appUserDataDir = appDirs.user_data_dir
        # Add trailing slash:
        appUserDataDir = os.path.join(appUserDataDir,"")
        if not os.path.exists(appUserDataDir):
            os.makedirs(appUserDataDir)
        global config
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        global cvlAdministratorPreferencesFilePath
        cvlAdministratorPreferencesFilePath = os.path.join(appUserDataDir,"CVL Administrator Preferences.cfg")
        if os.path.exists(cvlAdministratorPreferencesFilePath):
            config.read(cvlAdministratorPreferencesFilePath)

        tempFrame = wx.Frame(None, -1)
        tempFrame.Center()

        #cvlAdministratorURL = "https://www.cvlAdministrator.org.au/index.php?option=com_content&view=article&id=121"

        #try:
            #myHtmlParser = MyHtmlParser()
            #feed = urllib.urlopen(cvlAdministratorURL)
            #html = feed.read()
            #myHtmlParser.feed(html)
            #myHtmlParser.close()
        #except:
            #dlg = wx.MessageDialog(tempFrame, "Error: Unable to contact MASSIVE website to check version number.\n\n" +
                                        #"CVL Administrator cannot continue.\n",
                                #"CVL Administrator", wx.OK | wx.ICON_INFORMATION)
            #dlg.ShowModal()
            #dlg.Destroy()
            #sys.exit(1)


        #latestVersion = myHtmlParser.data[0].strip()

        dlg = wx.MessageDialog(tempFrame, "Warning: Bypassing version number check for now...\n", "CVL Administrator", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
        latestVersion = "0.0.1"

        if latestVersion!=cvl_administrator_version_number.version_number:
            newVersionAlertDialog = wx.Dialog(tempFrame, title="CVL Administrator", name="CVL Administrator",pos=(200,150),size=(680,290))

            if sys.platform.startswith("win"):
                _icon = wx.Icon('CVL Administrator.ico', wx.BITMAP_TYPE_ICO)
                newVersionAlertDialog.SetIcon(_icon)

            if sys.platform.startswith("linux"):
                import cvlAdministratorIcon
                newVersionAlertDialog.SetIcon(cvlAdministratorIcon.getMASSIVElogoTransparent128x128Icon())

            cvlAdministratorIconPanel = wx.Panel(newVersionAlertDialog)

            import cvlAdministratorIcon
            cvlAdministratorIconAsBitmap = cvlAdministratorIcon.getMASSIVElogoTransparent128x128Bitmap()
            wx.StaticBitmap(cvlAdministratorIconPanel, -1, 
                cvlAdministratorIconAsBitmap,
                (0, 50),
                (cvlAdministratorIconAsBitmap.GetWidth(), cvlAdministratorIconAsBitmap.GetHeight())) 

            newVersionAlertTextPanel = wx.Panel(newVersionAlertDialog)

            gs = wx.FlexGridSizer(rows=4, cols=1, vgap=5, hgap=5)
            newVersionAlertTextPanel.SetSizer(gs)

            newVersionAlertTitleLabel = wx.StaticText(newVersionAlertTextPanel,
                label = "CVL Administrator")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetPointSize(14)
            font.SetWeight(wx.BOLD)
            newVersionAlertTitleLabel.SetFont(font)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))
            gs.Add(newVersionAlertTitleLabel, flag=wx.EXPAND)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))

            newVersionAlertTextLabel1 = wx.StaticText(newVersionAlertTextPanel, 
                label = 
                "You are running version " + cvl_administrator_version_number.version_number + "\n\n" +
                "The latest version is " + myHtmlParser.data[0] + "\n\n" +
                "Please download a new version from:\n\n")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel1.SetFont(font)
            gs.Add(newVersionAlertTextLabel1, flag=wx.EXPAND)

            newVersionAlertHyperlink = wx.HyperlinkCtrl(newVersionAlertTextPanel, 
                id = wx.ID_ANY,
                label = cvlAdministratorURL,
                url = cvlAdministratorURL)
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(8)
            newVersionAlertHyperlink.SetFont(font)
            gs.Add(newVersionAlertHyperlink, flag=wx.EXPAND)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))

            newVersionAlertTextLabel2 = wx.StaticText(newVersionAlertTextPanel, 
                label = 
                "For queries, please contact:\n\nhelp@cvlAdministrator.org.au\njames.wettenhall@monash.edu\n")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel2.SetFont(font)
            gs.Add(newVersionAlertTextLabel2, flag=wx.EXPAND)

            def OnOK(event):
                sys.exit(1)

            okButton = wx.Button(newVersionAlertTextPanel, 1, ' OK ')
            okButton.SetDefault()
            gs.Add(okButton, flag=wx.ALIGN_RIGHT)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))
            gs.Fit(newVersionAlertTextPanel)

            newVersionAlertDialog.Bind(wx.EVT_BUTTON, OnOK, id=1)

            gs = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=5)
            gs.Add(cvlAdministratorIconPanel, flag=wx.EXPAND)
            gs.Add(newVersionAlertTextPanel, flag=wx.EXPAND)
            gs.Add(wx.StaticText(newVersionAlertDialog,label="       "))
            newVersionAlertDialog.SetSizer(gs)
            gs.Fit(newVersionAlertDialog)

            newVersionAlertDialog.ShowModal()
            newVersionAlertDialog.Destroy()

            sys.exit(1)
 
        global ec2CredentialsDialog
        ec2CredentialsDialog = wx.Dialog(tempFrame, title="CVL Administrator", name="CVL Administrator",size=(600,220))
        ec2CredentialsDialog.Center()
        ec2CredentialsPanel = wx.Panel(ec2CredentialsDialog)
        gs = wx.FlexGridSizer(rows=8, cols=6, vgap=5, hgap=5)
        ec2CredentialsPanel.SetSizer(gs)

        ec2CredentialsPanelTitleLabel = wx.StaticText(ec2CredentialsPanel, label = "CVL Administrator")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetPointSize(14)
        font.SetWeight(wx.BOLD)
        ec2CredentialsPanelTitleLabel.SetFont(font)
        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel));
        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(ec2CredentialsPanelTitleLabel); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel));

        ec2CredentialsZipFileLabel = wx.StaticText(ec2CredentialsPanel, label = "EC2 credentials zip file:")

        dummyPanel = wx.Panel(ec2CredentialsDialog)
        defaultTextFieldSize = wx.TextCtrl(dummyPanel, -1, "").GetSize()
        dummyPanel.Destroy()
        ec2CredentialsZipFilenameField = wx.TextCtrl(ec2CredentialsPanel, -1, "", size=(200, defaultTextFieldSize.height))

        def OnBrowse(self):
            filters = 'EC2 Credentials files (*.zip)|*.zip'
            openFileDialog = wx.FileDialog ( None, message = 'Open EC2 credentials zip file...', wildcard = filters, style = wx.OPEN)
            if openFileDialog.ShowModal() == wx.ID_OK:
                global ec2CredentialsZipFilePath
                ec2CredentialsZipFilePath = openFileDialog.GetPath()
                ec2CredentialsZipFilenameField.WriteText(ec2CredentialsZipFilePath)

        browseButton = wx.Button(ec2CredentialsPanel, 1, "Browse...")
        ec2CredentialsDialog.Bind(wx.EVT_BUTTON, OnBrowse, id=1)

        def OnHelp(self):
            import cStringIO
            import downloadingEC2CredentialsImage

            global bmp

            class DisplayDownloadingEC2CredentialsImage(wx.Panel):
                def __init__(self, parent, id):
                    wx.Panel.__init__(self, parent, id)
                    bmp = downloadingEC2CredentialsImage.getDownloadingEC2CredentialsBitmap()
                    wx.StaticBitmap(self, -1, bmp, (0, 0), (bmp.GetWidth(), bmp.GetHeight()))

            bmp = downloadingEC2CredentialsImage.getDownloadingEC2CredentialsBitmap()
            ec2ImageFrame = wx.Frame(None, -1, "CVL Administrator - How To Download EC2 Credentials From Nectar", size = (bmp.GetWidth(), bmp.GetHeight()))
            DisplayDownloadingEC2CredentialsImage(ec2ImageFrame,-1)
            ec2ImageFrame.Show(1)

        helpButton = wx.Button(ec2CredentialsPanel, 2, "Help...")
        ec2CredentialsDialog.Bind(wx.EVT_BUTTON, OnHelp, id=2)

        def OnOK(self):
            if ec2CredentialsZipFilePath.strip() != "":

                import zipfile
                zf = zipfile.ZipFile(ec2CredentialsZipFilePath)
                ec2rcFilename = 'ec2rc.sh'
                try:
                    info = zf.getinfo(ec2rcFilename)
                except KeyError:
                    print 'ERROR: Did not find %s in zip file' % ec2rcFilename
                else:
                    #print '%s is %d bytes' % (info.filename, info.file_size)
                    ec2rcContents = zf.read(ec2rcFilename)
                    stringBuffer = StringIO.StringIO(ec2rcContents)

                    line = "\n"
                    ec2_access_key = ""
                    ec2_secret_key = ""
                    while line!="":
                        line = stringBuffer.readline()
                        if "export EC2_ACCESS_KEY" in line:
                            lineSplit = line.split("=")
                            ec2_access_key = lineSplit[1].strip()
                            #print "EC2_ACCESS_KEY = " + ec2_access_key
                        if "export EC2_SECRET_KEY" in line:
                            lineSplit = line.split("=")
                            ec2_secret_key = lineSplit[1].strip()
                            #print "EC2_SECRET_KEY = " + ec2_secret_key

                    import boto
                    from boto.ec2.connection import EC2Connection
                    from boto.ec2.regioninfo import RegionInfo

                    region = RegionInfo(name="NeCTAR", endpoint="nova.rc.nectar.org.au")
                    global ec2Connection
                    ec2Connection = boto.connect_ec2(aws_access_key_id=ec2_access_key,
                        aws_secret_access_key=ec2_secret_key,
                        is_secure=False,
                        region=region,
                        port=8773,
                        path="/services/Cloud")

                    ec2CredentialsDialog.Destroy()
            else:
                dlg = wx.MessageDialog(None, "Error: Please upload a zip file containing your NeCTAR EC2 credentials, e.g. \"810-x509.zip\".",
                                "CVL Administrator", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()

        okButton = wx.Button(ec2CredentialsPanel, 3, "OK")
        ec2CredentialsDialog.Bind(wx.EVT_BUTTON, OnOK, id=3)

        def OnCancel(self):
            sys.exit(1)

        cancelButton = wx.Button(ec2CredentialsPanel, 4, "Cancel")
        ec2CredentialsDialog.Bind(wx.EVT_BUTTON, OnCancel, id=4)

        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel));
        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(ec2CredentialsZipFileLabel); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(ec2CredentialsZipFilenameField, flag=wx.EXPAND); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(browseButton, flag=wx.EXPAND);
        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel));
        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(helpButton, flag=wx.EXPAND);
        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel));
        gs.Add(wx.StaticText(ec2CredentialsPanel, -1, "               ")); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(cancelButton, flag=wx.ALIGN_RIGHT); gs.Add(wx.StaticText(ec2CredentialsPanel)); gs.Add(okButton, flag=wx.EXPAND);

        gs.Fit(ec2CredentialsPanel)

        ec2CredentialsDialog.ShowModal()

        global launchDialogFrame
        launchDialogFrame = MyFrame(None, -1, 'CVL Administrator')
        launchDialogFrame.Show(True)
        return True

app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
app.MainLoop()

