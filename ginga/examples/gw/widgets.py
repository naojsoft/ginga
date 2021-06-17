"""
Test program for trying widgets in the different wrapped toolkits supported
by Ginga.

Usage:
  $ python widgets.py <toolkit-name> [logging options]

Examples:
  $ python widgets.py -t qt5
  $ python widgets.py -t gtk3
  $ python widgets.py -t pg
"""
import sys
import os

from ginga.misc import log
from ginga.util.paths import icondir  # noqa

top = None


def quit(*args):
    if top is not None:
        top.delete()
    sys.exit()


def popup_dialog(parent):
    from ginga.gw import Widgets
    dia = Widgets.Dialog(title="Dialog Title",
                         buttons=[('ok', 0), ('cancel', 1)],
                         parent=parent, modal=True)
    cntr = dia.get_content_area()
    cntr.add_widget(Widgets.Label("My Dialog Content"))
    parent.add_dialog(dia)
    dia.show()


def show_example(cbox, top, logger):
    from ginga.gw import Widgets
    wname = cbox.get_text()
    vbox = Widgets.VBox()
    vbox.set_border_width(2)
    vbox.set_spacing(1)

    if wname == 'label':
        w = Widgets.Label("Hello World label")
        vbox.add_widget(w, stretch=1)

    elif wname == 'button':
        w = Widgets.Button("Press me")
        w.add_callback('activated', lambda w: logger.info("button was clicked"))
        w.add_callback('activated', lambda w: popup_dialog(top))
        vbox.add_widget(w, stretch=1)

    elif wname == 'textentry':
        w = Widgets.TextEntry()
        w.set_text("Hello, World!")
        w.add_callback('activated',
                       lambda w: logger.info("said '{}'".format(w.get_text())))
        vbox.add_widget(w, stretch=1)

    elif wname == 'textentryset':
        w = Widgets.TextEntrySet()
        w.set_text("Hello, World!")
        w.add_callback('activated',
                       lambda w: logger.info("said '{}'".format(w.get_text())))
        vbox.add_widget(w, stretch=1)

    elif wname == 'textarea':
        w = Widgets.TextArea(editable=True)
        w.set_text("Hello, World!")
        vbox.add_widget(w, stretch=1)

    elif wname == 'checkbox':
        w = Widgets.CheckBox("Check me")
        w.add_callback('activated',
                       lambda w, val: logger.info("value changed to '{}'".format(w.get_state())))
        vbox.add_widget(w, stretch=1)

    elif wname == 'dial':
        w = Widgets.Dial()
        w.set_limits(-20, 20, incr_value=1)
        w.add_callback('value-changed',
                       lambda w, val: logger.info("value changed to '{}'".format(w.get_value())))
        vbox.add_widget(w, stretch=1)

    elif wname == 'togglebutton':
        w = Widgets.ToggleButton("Toggle me")
        w.add_callback('activated',
                       lambda w, val: logger.info("value changed to '{}'".format(w.get_state())))
        vbox.add_widget(w, stretch=1)

    elif wname == 'radiobutton':
        w = Widgets.RadioButton("Option 1")
        w.add_callback('activated',
                       lambda w, val: logger.info("chose option 1"))
        vbox.add_widget(w)
        w2 = Widgets.RadioButton("Option 2", group=w)
        w2.add_callback('activated',
                        lambda w, val: logger.info("chose option 2"))
        vbox.add_widget(w2)
        w3 = Widgets.RadioButton("Option 3", group=w)
        w3.add_callback('activated',
                        lambda w, val: logger.info("chose option 3"))
        vbox.add_widget(w3)

    elif wname == 'combobox':
        w = Widgets.ComboBox()
        for name in ["Larry", "Curly", "Moe"]:
            w.append_text(name)
        w.add_callback('activated',
                       lambda w, val: logger.info("chose '{}'".format(w.get_text())))
        vbox.add_widget(w)

    elif wname == 'spinbox':
        w = Widgets.SpinBox(dtype=int)
        w.set_limits(-10, 10, incr_value=1)
        w.set_value(4)
        w.add_callback('value-changed',
                       lambda w, val: logger.info("chose {}".format(val)))
        vbox.add_widget(w)

    elif wname == 'slider':
        w = Widgets.Slider(orientation='horizontal')
        w.set_limits(-10, 10, incr_value=1)
        w.set_value(4)
        w.set_tracking(True)
        w.add_callback('value-changed',
                       lambda w, val: logger.info("chose {}".format(val)))
        vbox.add_widget(w)

    elif wname == 'scrollbar':
        w = Widgets.ScrollBar(orientation='horizontal')
        w.add_callback('activated', lambda w, val: logger.info("value is %d" % val))
        vbox.add_widget(w)

    elif wname == 'progressbar':
        w = Widgets.ProgressBar()
        w.set_value(0.6)
        vbox.add_widget(w)

    elif wname == 'statusbar':
        w = Widgets.StatusBar()
        w.set_message("Hello, World! is my status")
        vbox.add_widget(w)

    elif wname == 'image':
        w = Widgets.Image()
        w.load_file(os.path.join(icondir, 'ginga-512x512.png'))
        vbox.add_widget(w)

    elif wname == 'treeview':
        w = Widgets.TreeView(selection='single', sortable=True,
                             use_alt_row_color=True)
        columns = [("Meal", 'meal'), ("Critic 1", 'review1'),
                   ("Critic 2", 'review2'), ("Critic 3", 'review3')]
        w.setup_table(columns, 1, 'meal')
        tree = dict(Breakfast=dict(meal='Breakfast', review1="Delish!",
                                   review2="Ugh!", review3="Meh"),
                    Lunch=dict(meal='Lunch', review1="Gross!",
                               review2="Interesting...", review3="Meh"),
                    Supper=dict(meal='Supper', review1="Meh",
                                review2="Meh", review3="Jolly good!"))
        w.set_tree(tree)
        vbox.add_widget(w, stretch=1)

    elif wname == 'webview':
        w = Widgets.WebView()
        w.load_url("http://www.google.com/")
        vbox.add_widget(w)

    elif wname == 'frame':
        w = Widgets.Frame(title="Frame Title")
        w.set_widget(Widgets.Label("Framed content"))
        vbox.add_widget(w)

    elif wname == 'expander':
        w = Widgets.Expander(title="Expander Title")
        w.set_widget(Widgets.Label("Expander content"))
        vbox.add_widget(w)

    elif wname == 'hbox':
        w = Widgets.HBox()
        w.add_widget(Widgets.Label("Item 1"), stretch=0)
        w.add_widget(Widgets.Label("Item 2"), stretch=1)
        vbox.add_widget(w)

    elif wname == 'vbox':
        w = Widgets.VBox()
        w.add_widget(Widgets.Label("Item 1"), stretch=0)
        w.add_widget(Widgets.Label("Item 2"), stretch=1)
        vbox.add_widget(w)

    elif wname == 'splitter':
        w = Widgets.Splitter(orientation='horizontal')
        w.add_widget(Widgets.Label('Content of Pane 1'))
        w.add_widget(Widgets.Label('Content of Pane 2'))
        w.set_sizes([10, 20])
        vbox.add_widget(w, stretch=1)

    elif wname == 'scrollarea':
        w = Widgets.ScrollArea()
        img = Widgets.Image()
        img.load_file(os.path.join(icondir, 'ginga-512x512.png'))
        w.set_widget(img)
        vbox.add_widget(w, stretch=1)

    elif wname == 'tabwidget':
        w = Widgets.TabWidget()
        w.add_widget(Widgets.Label('Content of Tab 1'), title='Tab 1')
        w.add_widget(Widgets.Label('Content of Tab 2'), title='Tab 2')
        hbox = Widgets.HBox()
        sbox = Widgets.SpinBox(dtype=int)
        sbox.set_limits(0, 1, incr_value=1)
        sbox.set_value(0)
        sbox.add_callback('value-changed', lambda sbx, val: w.set_index(val))
        hbox.add_widget(sbox)
        vbox.add_widget(w, stretch=1)
        vbox.add_widget(hbox, stretch=0)

    elif wname == 'stackwidget':
        w = Widgets.StackWidget()
        w.add_widget(Widgets.Label('Content of Stack 1'))
        w.add_widget(Widgets.Label('Content of Stack 2'))
        vbox.add_widget(w, stretch=1)

    elif wname == 'mdiwidget':
        w = Widgets.MDIWidget()
        w.add_widget(Widgets.Label('Content of MDI Area 1'))
        w.add_widget(Widgets.Label('Content of MDI Area 2'))
        vbox.add_widget(w, stretch=1)

    elif wname == 'gridbox':
        w = Widgets.GridBox(rows=2, columns=2)
        w.add_widget(Widgets.Label('Content of Grid Area 1'), 0, 0)
        w.add_widget(Widgets.Label('Content of Grid Area 2'), 0, 1)
        w.add_widget(Widgets.Label('Content of Grid Area 3'), 1, 0)
        w.add_widget(Widgets.Label('Content of Grid Area 4'), 1, 1)
        vbox.add_widget(w, stretch=1)

    elif wname == 'menubar':
        w = Widgets.Menubar()
        menu = w.add_name('Menu 1')
        menu.add_name('Larry').add_callback('activated',
                                            lambda *args: print("chose Larry"))
        menu.add_name('Curly').add_callback('activated',
                                            lambda *args: logger.info("chose Curly"))
        menu.add_name('Moe').add_callback('activated',
                                          lambda *args: logger.info("chose Moe"))

        menu = w.add_name('3Amigos')
        menu.add_name('Hector').add_callback('activated',
                                             lambda *args: print("chose Hector"))
        menu.add_name('Manuel').add_callback('activated',
                                             lambda *args: logger.info("chose Manuel"))
        menu.add_name('Roberto').add_callback('activated',
                                              lambda *args: logger.info("chose Roberto"))
        vbox.add_widget(w)
        vbox.add_widget(Widgets.Label("App content"), stretch=1)

    elif wname == 'toolbar':
        w = Widgets.Toolbar()
        menu = w.add_menu('Menu Type 1', mtype='tool')
        menu.add_name('Larry').add_callback('activated',
                                            lambda w: logger.info("chose Larry"))
        menu.add_name('Curly').add_callback('activated',
                                            lambda w: logger.info("chose Curly"))
        menu.add_name('Moe').add_callback('activated',
                                          lambda w: logger.info("chose Moe"))
        menu = w.add_menu('Menu Type 2', mtype='mbar')
        menu.add_name('Frank')
        menu.add_name('Dean')
        menu.add_name('Sammy')
        w.add_widget(Widgets.Button('A Button'))
        w.add_separator()
        w.add_action("Toggle me", toggle=True)
        w.add_action(None, iconpath=os.path.join(icondir, 'hand_48.png'))
        vbox.add_widget(w)
        vbox.add_widget(Widgets.Label("App content"), stretch=1)

    elif wname == 'dialog':
        dia = Widgets.Dialog(title="Dialog Title",
                             buttons=[('ok', 0), ('cancel', 1)],
                             parent=top, modal=False)
        dia.add_callback('activated',
                         lambda w, rsp: logger.info("user chose %s" % (rsp)))
        top.add_dialog(dia)
        cntr = dia.get_content_area()
        cntr.add_widget(Widgets.Label("My Dialog Content"))

        # add some content to main app widget
        w = Widgets.Label("Hello World label")
        vbox.add_widget(w, stretch=1)
        hbox = Widgets.HBox()
        w = Widgets.Button("Open Dialog")
        w.add_callback('activated', lambda w: dia.show())
        hbox.add_widget(w)
        w = Widgets.Button("Close Dialog")
        w.add_callback('activated', lambda w: dia.hide())
        hbox.add_widget(w)
        vbox.add_widget(hbox)

    else:
        # default to label
        logger.error("Don't understand kind of widget '%s'" % (wname))
        w = Widgets.Label("Hello World label")
        vbox.add_widget(w, stretch=1)

    dia = Widgets.Dialog(title="Example: " + wname,
                         parent=top, modal=False)
    dia.add_callback('close', lambda *args: dia.delete())
    cntr = dia.get_content_area()
    cntr.add_widget(vbox)
    if hasattr(top, 'add_dialog'):
        top.add_dialog(dia)
    dia.show()


def main(options, args):
    logger = log.get_logger('test', options=options)

    import ginga.toolkit as ginga_toolkit

    ginga_toolkit.use(options.toolkit)

    from ginga.gw import Widgets

    app = Widgets.Application(logger=logger)
    app.add_callback('shutdown', quit)

    page = None
    if hasattr(app, 'script_imports'):
        app.script_imports.append('jqx')

        top = Widgets.Page(title="Ginga Wrapped Widgets")
        app.add_window(top)
    else:
        top = app.make_window("Ginga Wrapped Widgets")

    top.add_callback('close', quit)

    hbox = Widgets.HBox()
    hbox.set_border_width(2)
    hbox.set_spacing(1)

    cbox = Widgets.ComboBox()
    for wname in ['label', 'button', 'textentry', 'textentryset', 'textarea',
                  'checkbox', 'togglebutton', 'radiobutton', 'combobox',
                  'spinbox', 'slider', 'scrollbar', 'progressbar', 'statusbar',
                  'image', 'treeview', 'webview', 'frame', 'expander',
                  'hbox', 'vbox', 'splitter', 'scrollarea', 'tabwidget',
                  'stackwidget', 'mdiwidget', 'gridbox', 'menubar', 'toolbar',
                  'dialog', 'dial']:
        cbox.insert_alpha(wname)

    hbox.add_widget(cbox)
    btn = Widgets.Button("Show Example")
    btn.add_callback('activated', lambda w: show_example(cbox, top, logger))
    hbox.add_widget(btn)

    top.set_widget(hbox)
    top.show()
    top.raise_()

    try:
        app.mainloop()

    except KeyboardInterrupt:
        print("Terminating viewer...")
        if top is not None:
            top.close()


if __name__ == "__main__":
    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                        default='qt',
                        help="Choose GUI toolkit (gtk|qt|pg)")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    main(options, args)
