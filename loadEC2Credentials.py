import wx
import StringIO

application = wx.PySimpleApp()

# Create a list of filters

# This should be fairly simple to follow, so no explanation is necessary

filters = 'EC2 Credentials files (*.zip)|*.zip'

dialog = wx.FileDialog ( None, message = 'Open something....', wildcard = filters, style = wx.OPEN)

if dialog.ShowModal() == wx.ID_OK:

    # We'll have to make room for multiple files here

    selected = dialog.GetPath()

    print 'Selected:', selected

    import zipfile

    zf = zipfile.ZipFile(selected)
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
        while line!="":
            line = stringBuffer.readline()
            if "export EC2_ACCESS_KEY" in line:
                lineSplit = line.split("=")
                ec2_access_key = lineSplit[1].strip()
                print "EC2_ACCESS_KEY = " + ec2_access_key
            if "export EC2_SECRET_KEY" in line:
                lineSplit = line.split("=")
                ec2_secret_key = lineSplit[1].strip()
                print "EC2_SECRET_KEY = " + ec2_secret_key

else:

    print 'Nothing was selected.'

dialog.Destroy()

