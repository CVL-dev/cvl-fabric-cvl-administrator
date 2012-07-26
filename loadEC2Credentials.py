from wxPython.wx import *

application = wxPySimpleApp()

# Create a list of filters

# This should be fairly simple to follow, so no explanation is necessary

filters = 'EC2 Credentials files (*.zip)|*.zip'

dialog = wxFileDialog ( None, message = 'Open something....', wildcard = filters, style = wxOPEN)

if dialog.ShowModal() == wxID_OK:

    # We'll have to make room for multiple files here

    selected = dialog.GetPath()

    print 'Selected:', selected

    import zipfile

    zf = zipfile.ZipFile(selected)
    filename = 'ec2rc.sh'
    try:
        info = zf.getinfo(filename)
    except KeyError:
        print 'ERROR: Did not find %s in zip file' % filename
    else:
        print '%s is %d bytes' % (info.filename, info.file_size)
        data = zf.read(filename)
        #print repr(data)
        print data

else:

    print 'Nothing was selected.'

dialog.Destroy()

