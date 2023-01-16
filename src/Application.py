from functools import partial
from graphviz import Digraph
from PIL import Image, ImageTk
from pathlib import Path
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import font
import configparser
import csv
import datetime
import os
import PartsView 
import platform
import sys
import textwrap
import time
import tkinter as tk
import uuid
import xml.etree.ElementTree as ET



class Application(tk.Frame):
    def __init__(self, version, master=None, testmode=False):
        super().__init__(master)
        self.set_uuid()
        self.set_os()
        self.set_dirs()
        self.set_mode()
        self.diff_version(version)
        self.create_configfile()
        self.set_config()
        self.set_sizes()
        self.set_objects(master)
        self.set_temporary_values()
        self.set_files()
        self.set_graph_attr() 
        self.set_window_geometry()
        self.create_panedwindow()
        self.create_canvas()
        self.create_outliner()
        self.create_scrollbar()
        self.create_menubar()
        self.create_contextmenu()
        self.pack_widgets()
        self.set_events()
        self.set_history()
        self.create_logfile()
        self.initial_call()

        self.update()
        self.show_tutorial()

        if testmode == True:
            self.master.after(3600000, self.notify_test_is_complete)

    def add_node(self, parent_iid, nodename, nodetype, operator='or', log='', is_reset_fig=True):
        #改行文字の自動挿入
        nodename = self.arrenge_nodename(nodename)

        #outlinerへの挿入
        child_iid = self.outliner.insert(
            parent=parent_iid, index='end',text=nodename, tags=(nodetype,operator), open="True")
        self.outliner.selection_set(child_iid)
        self.outliner.focus(child_iid)

        #graphvizへの挿入
        if nodetype == 'pattern':
            self.graph.node(
                child_iid, nodename, fontname=self.fontname_pattern,
                fontcolor=self.fontcolor_pattern, style=self.style_pattern, 
                fillcolor=self.fillcolor_pattern, penwidth=self.penwidth_pattern)
        elif nodetype == 'free':
            self.graph.node(
                child_iid, nodename, fontname=self.fontname_free,
                fontcolor=self.fontcolor_free, style=self.style_free, 
                fillcolor=self.fillcolor_free, penwidth=self.penwidth_free)
        else:
            print('ERROR on add_node : [' + repr(nodetype) + '] tag is not specified.')

        if not parent_iid == '':
            if operator == 'or':self.graph.edge(parent_iid,child_iid, arrowtail='normal')
            elif operator == 'and':self.graph.edge(parent_iid,child_iid, arrowtail='onormal')
            else:print('ERROR on add_node : [' + repr(operator) + '] operator is not specified.')

        #再描画
        if is_reset_fig == True:self.reset_fig(is_reset_graph=False, is_add_history=True)

        #log出力
        self.output_log('add', log, child_iid, nodename, nodetype, operator, parent_iid)

        return child_iid

    def add_history(self):
        if self.index_now < len(self.history_stack)-1:
            del self.history_stack[self.index_now+1:len(self.history_stack)]
        
        self.create_output()
        self.history_stack.append(self.output_xml)
        self.index_now += 1
        self.reset_title()

    def arrenge_nodename(self, nodename):
        if self.is_automatic_lfcode_insertion == True:
            nodename = ' \\n '.join(textwrap.wrap(nodename, width=self.nodename_length))
        return nodename

    def change_dpi(self, ratio):
        self.fig_dpi = int(72 * ratio)
        self.graph.attr('graph', dpi=str(self.fig_dpi))
        self.reset_fig(is_reset_graph=False, is_add_history=False)

    def change_node(self, iid, nodename, nodetype, operator, log=''):
        parent_iid = self.outliner.parent(iid)

        self.outliner.item(iid, text=nodename, tags=(nodetype,operator))
        self.reset_fig(is_reset_graph=True, is_add_history=True)

        self.reset_fig(is_reset_graph=True, is_add_history=True)

        #log出力
        self.output_log('change', log, iid, nodename, nodetype, operator, parent_iid)

    def change_selection(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
            if self.selected_iid == '':return 0

        nodename_old=self.outliner.item(self.selected_iid,'text')
        nodetype_old=self.outliner.item(self.selected_iid,'tags')[0]
        operator_old=self.outliner.item(self.selected_iid,'tags')[1]

        nodename_new, nodetype_new, operator_new  = self.get_nodename(
            window_title='ノードを変更', 
            default_text=nodename_old,
            default_type=nodetype_old,
            default_operator=operator_old
            )
        
        if nodename_new == '' or nodetype_new == '' or operator_new == '':return 0
        if nodename_new != nodename_old or nodetype_new != nodetype_old or operator_new != operator_old:
            self.change_node(
                self.selected_iid, nodename_new, nodetype_new, operator_new, log='change selection')

        #通常時値は入れない
        self.selected_iid = ''

    def change_mode_lfcode(self, val):
        self.is_automatic_lfcode_insertion = val

    def close_window(self):
        if self.index_now != self.index_saved:
            if messagebox.askyesno(title='保存確認', message='変更を保存しますか？'):
                self.save()

        self.output_log('close', 'close file', '', '', '', '', '')
        self.output_log('close', 'close app', '', '', '', '', '')
        self.master.destroy()

    def copy_subtrees(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
        if self.selected_iid == '':return 0

        child_nodes_tuple = self.get_child_nodes(self.selected_iid)
        iid_subtrees = list((self.selected_iid,) + child_nodes_tuple)

        subtrees = []
        for node_iid in iid_subtrees:
            iid = node_iid
            nodename = self.outliner.item(node_iid, 'text')
            nodetype = self.outliner.item(node_iid, 'tags')[0]
            operator = self.outliner.item(node_iid, 'tags')[1]
            parent_iid = self.outliner.parent(node_iid)
            subtrees.append((iid, nodename, nodetype, operator, parent_iid))

            log = 'copy from ' + self.output_filename
            self.output_log('copy', log, iid, nodename, nodetype, operator, parent_iid)

        self.clipboard_clear()
        self.clipboard_append(repr(subtrees))

        #通常時値は入れない
        self.selected_iid = ''

    def create_canvas(self):
        canvas_bgcolor = self.config_ini.get(self.config_section_name, 'canvas_bgcolor')
        self.attackcanvas = tk.Canvas(
            self.panedwindow_right, width=self.canvas_width, 
            height=self.canvas_height,scrollregion=self.canvas_scrollregion,bg=canvas_bgcolor)

    def create_configfile(self):
        #configを上書きして良いか確認
        if self.is_configfile_updatable == False:return 0

        #ローカルにconfig.iniを作成
        self.config_writer = configparser.ConfigParser()

        self.config_writer['DEFAULT'] = {
            'arrowhead' : 'none',
            'arrowtail' : 'normal',
            'border_width_of_panedwindow' : '5',
            'capec_filename' : 'parts_list_from_capec.xml',
            'canvas_bgcolor' : 'white',
            'color_of_attentionnode' : '#4EABE3',
            'color_of_freenode' : 'black',
            'color_of_patternnode' : 'black',
            'edge_direction' : 'both',
            'figdpi' : '72',
            'figname_on_render' : 'attacktrees.png',
            'fig_output_dir' : '~/Downloads',
            'fillcolor_of_freenode' : 'white',
            'fillcolor_of_patternnode' : '#FFF280',
            'fontcolor_of_freenode' : 'black',
            'fontcolor_of_patternnode' : 'black',
            'fontsize_of_reuseconditions' : '16',
            'inputwindow_height' : '210',
            'inputwindow_width' : '250',
            'length_per_line_of_nodename' : '20',
            'log_filename' : 'log.csv',
            'node_shape' : 'box',
            'parts_figname_on_render' : 'parts.png',
            'penwidth_of_attentionnode' : '3',
            'penwidth_of_freenode' : '1',
            'penwidth_of_patternnode' : '1',
            'ratio_between_height_of_frametopright_to_window_on_partsview' : '0.7',
            'ratio_between_size_of_window_to_screen' : '0.8',
            'ratio_between_size_of_partview_window_to_screen' : '0.8',
            'ratio_between_width_of_panedleft_to_window' : '0.2',
            'ratio_between_width_of_frameleft_to_window_on_partsview' : '0.3',
            'style_of_patternnode' : 'filled',
            'style_of_freenode' : 'filled',
            'tutorial_window_height' : '650',
            'tutorial_window_width' : '600',
            'version' : self.version
        }

        self.config_writer['WINDOWS'] = {
            'fontname_of_freenode' : 'Yu Gothic', 
            'fontname_of_patternnode' : 'Yu Gothic'
        }

        self.config_writer['MACOS'] = {
            'fontname_of_freenode' : 'Hiragino Kaku Gothic Pro', 
            'fontname_of_patternnode' : 'Hiragino Kaku Gothic Pro'
        }

        with open(self.config_path, 'w') as file:
            self.config_writer.write(file)

    def create_contextmenu(self):
        if self.os_name == 'Windows':modifier_key = 'Control'
        if self.os_name == 'Mac':modifier_key = 'Command'

        self.contextmenu = tk.Menu(self.master)
        self.contextmenu.add_command(label='子ノードを作成', command=self.insert_child, accelerator='Return')
        self.contextmenu.add_command(label='弟ノードを作成', command=self.insert_brother, accelerator='Tab')
        self.contextmenu.add_command(label='ノードを編集', command=self.change_selection, accelerator=modifier_key + '+e')
        self.contextmenu.add_separator()
        self.contextmenu.add_command(label='コピー', command=self.copy_subtrees, accelerator=modifier_key + '+c')
        self.contextmenu.add_command(label='カット', command=self.cut_subtrees, accelerator=modifier_key + '+x')
        self.contextmenu.add_command(label='ペースト', command=self.paste_subtrees, accelerator=modifier_key + '+v')
        self.contextmenu.add_separator()
        self.contextmenu.add_command(label='ノードを上（左）に移動', command=self.move_outlineitem_up, accelerator=modifier_key + '+u')
        self.contextmenu.add_command(label='ノードを下（右）に移動', command=self.move_outlineitem_down, accelerator=modifier_key + '+d')
        self.contextmenu.add_separator()
        self.contextmenu.add_command(label='ノードを削除', command=self.delete_selection, accelerator='BackSpace')

    def create_input_window(self, window_title='ノードを追加', default_text='', default_type='free', default_operator='or'):
        #raw文字列から戻す処理
        if default_text != '':
            try:
                default_text = eval('\''+default_text+'\'')
            except SyntaxError as e:
                print(e)

        #サブウィンドウ生成
        self.input_window = tk.Toplevel()
        self.input_window.title(window_title)
        self.input_window.geometry(
            str(self.inputwin_width) + 'x' + 
            str(self.inputwin_height) + '+' + 
            str(int(self.screen_width/2 - self.inputwin_width/2)) + '+' + 
            str(int(self.screen_height/2 - self.inputwin_height/2)))
        
        #モーダルモード
        self.input_window.grab_set()
        self.input_window.focus_set()

        #ラジオボタンをまとめるフレーム
        frame_radios = ttk.Frame(self.input_window, relief=tk.FLAT, padding=[10,10,10,10])

        #and - or ラジオボタン
        frame_operator = tk.LabelFrame(frame_radios, text='接続タイプ')
        var_operator = tk.IntVar()
        radio_or = tk.Radiobutton(frame_operator, value=0, variable=var_operator, text='[or] 接続')
        radio_and = tk.Radiobutton(frame_operator, value=1, variable=var_operator, text='[and] 接続')

        if default_operator == 'or':var_operator.set(0)
        else:var_operator.set(1)

        #ノードタイプ　ラジオボタン
        frame_type = tk.LabelFrame(frame_radios, text='ノードタイプ')
        var_type = tk.IntVar()
        radio_free = tk.Radiobutton(frame_type, value=0, variable=var_type, text='フリーノード')
        radio_pattern = tk.Radiobutton(frame_type, value=1, variable=var_type, text='パターンノード')

        if default_type == 'free':var_type.set(0)
        else:var_type.set(1)

        #テキストボックス
        frame_text = ttk.Frame(self.input_window, relief=tk.FLAT, padding=[10,0,10,0])
        textbox = tk.Text(frame_text, height=5, width=40)

        #OKボタン
        frame_button = ttk.Frame(self.input_window, relief=tk.FLAT, padding=[10,5,10,10])
        button = tk.Button(frame_button, text='OK')

        #イベント処理（raw文字列に変換）
        def ok_click(event=None):
            self.input_text = textbox.get(1.0, 'end-1c')
            self.input_text = repr(self.input_text).strip('\'')

            if var_operator.get() == 0:self.operator = 'or'
            else:self.operator = 'and'

            if var_type.get() == 0:self.nodetype = 'free'
            else:self.nodetype = 'pattern'

            self.input_window.destroy()

        def close_click():self.input_window.destroy()

        #バインド
        self.input_window.protocol('WM_DELETE_WINDOW', close_click)
        button['command'] = ok_click
        textbox.bind('<Key-Return>', ok_click)
        textbox.bind('<Control-Key-Return>', lambda e:0)

        #ウィジェットの配置
        frame_radios.pack(side=tk.TOP, fill=tk.X)
        frame_text.pack(side=tk.TOP, fill=tk.X)
        frame_button.pack(side=tk.TOP, fill=tk.X)

        frame_type.pack(side=tk.LEFT, fill=tk.X)
        frame_operator.pack(side=tk.RIGHT, fill=tk.X)

        radio_free.pack(side=tk.TOP, anchor=tk.W)
        radio_pattern.pack(side=tk.TOP, anchor=tk.W)
        radio_or.pack(side=tk.TOP, anchor=tk.W)
        radio_and.pack(side=tk.TOP, anchor=tk.W)
        textbox.pack(side=tk.TOP, fill=tk.X)
        button.pack(side=tk.TOP, fill=tk.BOTH)

        textbox.insert(1.0, default_text)
        textbox.focus_set()

    def create_logfile(self):
        self.log_filepath = os.path.join(self.log_dir, self.log_filename)

        is_create_newfile = False
        if os.path.isfile(self.log_filepath):
            if self.is_configfile_updatable == True:is_create_newfile = True
            else:is_create_newfile = False
        else:is_create_newfile = True

        if is_create_newfile == True:
            with open(self.log_filepath, 'w') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'datetime', 'operation', 'detail', 'iid', 'nodename', 
                    'nodetype', 'operator', 'parent_iid', 'filename', 'uuid'
                    ])

    def create_menubar(self):
        if self.os_name == 'Windows':modifier_key = 'Control'
        if self.os_name == 'Mac':modifier_key = 'Command'

        #メニューバー本体
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        #ファイルメニュー
        menu_file = tk.Menu(self.master)
        self.menubar.add_cascade(label='ファイル', menu=menu_file)

        menu_file.add_command(label='開く', command=self.read_file, accelerator=modifier_key + '+o')
        menu_file.add_command(label='保存', command=self.save, accelerator=modifier_key + '+s')
        menu_file.add_command(label='別名で保存', command=self.save_as, accelerator=modifier_key + '+Shift+s')

        menu_outputfig = tk.Menu(self.master)
        menu_file.add_cascade(label='画像を出力', menu=menu_outputfig)

        menu_outputfig.add_command(label='大 (dpi=504)', command=partial(self.output_fig, '504'))
        menu_outputfig.add_command(label='中 (dpi=360)', command=partial(self.output_fig, '360'))
        menu_outputfig.add_command(label='小 (dpi=216)', command=partial(self.output_fig, '216'))

        #編集メニュー
        menu_edit = tk.Menu(self.master)
        self.menubar.add_cascade(label='編集', menu=menu_edit)
        menu_edit.add_command(label='UnDo', command=self.undo, accelerator=modifier_key + '+z')
        menu_edit.add_command(label='ReDo', command=self.redo, accelerator=modifier_key + '+Shift+z')
        menu_edit.add_separator()
        menu_edit.add_command(label='子ノードを作成', command=self.insert_child, accelerator='Return')
        menu_edit.add_command(label='弟ノードを作成', command=self.insert_brother, accelerator='Tab')
        menu_edit.add_command(label='ノードを編集', command=self.change_selection, accelerator=modifier_key + '+e')
        menu_edit.add_separator()
        menu_edit.add_command(label='コピー', command=self.copy_subtrees, accelerator=modifier_key + '+c')
        menu_edit.add_command(label='カット', command=self.cut_subtrees, accelerator=modifier_key + '+x')
        menu_edit.add_command(label='ペースト', command=self.paste_subtrees, accelerator=modifier_key + '+v')
        menu_edit.add_separator()
        menu_edit.add_command(label='ノードを上（左）に移動', command=self.move_outlineitem_up, accelerator=modifier_key + '+u')
        menu_edit.add_command(label='ノードを下（右）に移動', command=self.move_outlineitem_down, accelerator=modifier_key + '+d')
        menu_edit.add_separator()
        menu_edit.add_command(label='ノードを削除', command=self.delete_selection, accelerator='BackSpace')

        #表示メニュー
        menu_display = tk.Menu(self.master)
        self.menubar.add_cascade(label='表示', menu=menu_display)

        menu_display.add_command(label='キャンバスを拡大', command=self.increase_dpi, accelerator=modifier_key + '++')
        menu_display.add_command(label='キャンバスを縮小', command=self.decrease_dpi, accelerator=modifier_key + '+-')

        #表示 = 画像の表示倍率
        dpi_ratio = tk.Menu(menu_display, tearoff=False)
        val_dpi_ratio = tk.IntVar()
        val_dpi_ratio.set(0)

        ratio_list = [1000,900,800,700,600,500,400,300,200,100,50,25]
        for ratio in ratio_list:
            dpi_ratio.add_radiobutton(
                label=str(ratio)+'%', 
                command=partial(self.change_dpi, ratio/100), 
                variable=val_dpi_ratio, 
                indicatoron=False)

        menu_display.add_cascade(label='キャンバスの表示倍率', menu=dpi_ratio)

        #ラジオメニューの初期選択
        dpi_ratio.invoke(9)

        #再利用メニュー
        menu_reuse = tk.Menu(self.master)
        self.menubar.add_cascade(label='再利用', menu=menu_reuse)
        menu_reuse.add_command(label='パーツ検索ビューを表示', command=self.show_partsview, accelerator=modifier_key + '+r')

        #チュートリアルメニュー
        menu_tutorial = tk.Menu(self.master)
        self.menubar.add_cascade(label='チュートリアル', menu=menu_tutorial)
        menu_tutorial.add_command(label='その1 アタックツリーを作ろう', command=self.tutorial_1)
        menu_tutorial.add_command(label='その2 パーツを再利用しよう', command=self.tutorial_2)

    def create_outliner(self):
        self.outliner = ttk.Treeview(self.panedwindow_left, height=self.window_height, show='tree', selectmode=tk.BROWSE)
        self.outliner.column('#0', stretch=False, width=self.window_width)

        self.outliner.tag_configure(
            'free', 
            foreground=self.fontcolor_free,
            background=self.fillcolor_free
            )
        self.outliner.tag_configure(
            'pattern', 
            foreground=self.fontcolor_pattern,
            background=self.fillcolor_pattern
            )

        #ペインウィンドウのリサイズ
        self.panedwindow_main.paneconfig(self.panedwindow_left, width=self.panedleft_width)

    def create_output(self):
        output_xml_root = ET.Element('AttackTrees')

        output_xml_info = ET.Element('Information')
        output_xml_info.set('AppVersion', self.version)
        output_xml_info.set('UUID', str(self.uuid))
        output_xml_root.append(output_xml_info)

        output_xml_nodes = ET.Element('Nodes')
        output_xml_root.append(output_xml_nodes)

        list_node_iids = self.get_child_nodes()
        for node_iid in list_node_iids:
            iid = node_iid
            nodename = self.outliner.item(node_iid, 'text')
            nodetype = self.outliner.item(node_iid, 'tags')[0]
            operator = self.outliner.item(node_iid, 'tags')[1]
            parent_iid = self.outliner.parent(node_iid)

            output_xml_node = ET.Element('Node')
            output_xml_node.set('ID', iid)
            output_xml_node.set('Name', nodename)
            output_xml_node.set('Type', nodetype)
            output_xml_node.set('Operator', operator)
            output_xml_node.set('ParentID', parent_iid)
            output_xml_nodes.append(output_xml_node)

        self.output_xml = ET.ElementTree(output_xml_root)

    def create_scrollbar(self):
        self.canvas_xbar = tk.Scrollbar(self.panedwindow_right, orient=tk.HORIZONTAL)
        self.canvas_ybar = tk.Scrollbar(self.panedwindow_right, orient=tk.VERTICAL)
        self.canvas_xbar.config(command=self.attackcanvas.xview)
        self.canvas_ybar.config(command=self.attackcanvas.yview)
        self.attackcanvas.config(xscrollcommand=self.canvas_xbar.set)
        self.attackcanvas.config(yscrollcommand=self.canvas_ybar.set)
        
        self.outliner_xbar = tk.Scrollbar(self.panedwindow_left, orient=tk.HORIZONTAL)
        self.outliner_ybar = tk.Scrollbar(self.panedwindow_left, orient=tk.VERTICAL)
        self.outliner_xbar.config(command=self.outliner.xview)
        self.outliner_ybar.config(command=self.outliner.yview)
        self.outliner.config(xscrollcommand=self.outliner_xbar.set)
        self.outliner.config(yscrollcommand=self.outliner_ybar.set)
      
    def create_panedwindow(self):
        self.panedleft_width = int(self.window_width*self.panedwindow_ratio)
        self.panedright_width = self.window_width - self.panedleft_width - self.panedborder_width

        self.panedwindow_main = tk.PanedWindow(
            self.master, 
            orient='horizontal', 
            sashrelief=tk.RAISED, 
            sashwidth=self.panedborder_width)

        self.panedwindow_left = tk.PanedWindow(
            self.panedwindow_main, 
            orient='vertical', 
            width=self.panedleft_width)

        self.panedwindow_right = tk.PanedWindow(
            self.panedwindow_main, 
            orient='vertical')

    def cut_subtrees(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
        if self.selected_iid == '':return 0

        child_nodes_tuple = self.get_child_nodes(self.selected_iid)
        iid_subtrees = list((self.selected_iid,) + child_nodes_tuple)

        subtrees = []
        for node_iid in iid_subtrees:
            iid = node_iid
            nodename = self.outliner.item(node_iid, 'text')
            nodetype = self.outliner.item(node_iid, 'tags')[0]
            operator = self.outliner.item(node_iid, 'tags')[1]
            parent_iid = self.outliner.parent(node_iid)
            subtrees.append((iid, nodename, nodetype, operator, parent_iid))

        self.clipboard_clear()
        self.clipboard_append(repr(subtrees))
        self.delete_node(self.selected_iid, log='cut subtree')

        #通常時値は入れない
        self.selected_iid = ''

    def decrease_dpi(self, event=None):
        if self.fig_dpi * 0.75 < 18:self.fig_dpi = 18
        else:self.fig_dpi = self.fig_dpi * 0.75
        self.graph.attr('graph', dpi=str(self.fig_dpi))
        self.reset_fig(is_reset_graph=False, is_add_history=False)

    def delete_node(self, iid, log=''):
        nodename = self.outliner.item(iid,'text')
        nodetype = self.outliner.item(iid,'tags')[0]
        operator = self.outliner.item(iid,'tags')[1]
        parent_iid = self.outliner.parent(iid)

        self.outliner.delete(iid)

        self.reset_fig(is_reset_graph=True, is_add_history=True)

        #log出力
        self.output_log('delete', log, iid, nodename, nodetype, operator, parent_iid)

    def delete_selection(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
        if self.selected_iid == '':return 0

        self.delete_node(self.selected_iid, log='delete selection')

        #通常時値は入れない
        self.selected_iid = ''

    def inputwindow_state_is(self):
        state_is = 'None'

        if self.input_window is not None:
            try:self.input_window.winfo_exists()
            except Exception as e:print(e)

            if self.input_window.winfo_exists():
                state_is = 'Open'
            else:
                state_is = 'Close'

        return state_is

    def diff_version(self, version):
        self.version = version
        self.is_configfile_updatable = False

        #version keyが無いか異なっていたらTrueを返す
        self.config_path = os.path.join(self.rattata_dir, 'config.ini')
        config_checker = configparser.ConfigParser()

        if os.path.isfile(self.config_path):
            config_checker.read(self.config_path)
        else:
            self.is_configfile_updatable = True
            return 0

        if not config_checker.has_option('DEFAULT', 'version'):
            self.is_configfile_updatable = True
            return 0
            
        if not config_checker.get('DEFAULT', 'version') == version:
            self.is_configfile_updatable = True
        else:
            self.is_configfile_updatable = False

    def expand_canvas(self):
        new_width = self.canvas_width
        new_height = self.canvas_height

        if self.attackimage_raw.width > self.canvas_width:
            new_width += 100 * (5 + int((self.attackimage_raw.width - self.canvas_width) / 100))

        if self.attackimage_raw.height > self.canvas_height:
            new_height += 100 * (5 + int((self.attackimage_raw.height - self.canvas_height) / 100))

        self.resize_canvas(new_width, new_height)

    def get_child_nodes(self, parent_iid=''):
        child_iid_tuple = self.outliner.get_children(parent_iid)
        for child_iid in child_iid_tuple:
            child_iid_tuple += self.get_child_nodes(child_iid)
        return child_iid_tuple

    def get_home_dir(self, dir_name):
        path = Path(os.path.dirname(__file__))
        _index = 0
        while True:
            if path.parents[_index].name == dir_name:
                home_dir = path.parents[_index]
                break
            _index += 1
        return home_dir

    def get_nodename(self, window_title='ノードを追加', default_text='', default_type='free', default_operator='or'):
        self.input_text = ''
        self.nodetype = ''
        self.operator = ''
        self.create_input_window(
            window_title=window_title, 
            default_text=default_text, 
            default_type=default_type,
            default_operator=default_operator
            )
        self.master.wait_window(self.input_window)
        return (self.input_text, self.nodetype, self.operator)

    def get_inputfile(self):
        if self.inputwindow_state_is() == 'Open':self.input_window.destroy()

        attacktrees_xml = None

        type = [('XMLファイル','*.xml')] 
        dir = self.output_dir
        input_filename = filedialog.askopenfilename(filetypes = type, initialdir = dir)

        if input_filename != '':
            attacktrees_xml = ET.parse(input_filename)
            self.output_filename = input_filename

        return attacktrees_xml

    def image_dragged(self, event):
        img_id = self.attackcanvas.find_closest(event.x, event.y)
        delta_x = event.x - self.pre_x
        delta_y = event.y - self.pre_y

        self.img_x = self.img_x + delta_x
        self.img_y = self.img_y + delta_y
        self.attackcanvas.coords(img_id, self.img_x, self.img_y)
        self.pre_x = event.x
        self.pre_y = event.y

    def image_pressed(self, event):
        self.pre_x = event.x
        self.pre_y = event.y

    def increase_dpi(self, event=None):
        if self.fig_dpi * 1.25 > 720:self.fig_dpi = 720
        else:self.fig_dpi = self.fig_dpi * 1.25
        self.graph.attr('graph', dpi=str(self.fig_dpi))

        self.reset_fig(is_reset_graph=False, is_add_history=False)

    def initial_call(self):
        self.output_log('open', 'open app', '', '', '', '', '')
        self.output_log('open', 'open new file', '', '', '', '', '')
        self.add_node('', 'ルートノード', 'free', log='add', is_reset_fig=False)
        self.reset_fig(is_reset_graph=False, is_add_history=False)

    def insert_brother(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
        if self.selected_iid == '':return 0

        parent_iid = self.outliner.parent(self.selected_iid)
        nodename, nodetype, operator  = self.get_nodename()
        if (nodename != ''):
            self.add_node(
                parent_iid, nodename, nodetype, operator, log='insert brother')

        #通常時値は入れない
        self.selected_iid = ''

    def insert_child(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()

        #親ノードを展開する
        if self.selected_iid != '':
            self.outliner.item(self.selected_iid, open=True)
            self.reset_fig(is_reset_graph=True, is_add_history=False)

        nodename, nodetype, operator = self.get_nodename()
        if (nodename != ''):
            self.add_node(
                self.selected_iid, nodename, nodetype, operator, log='insert child')

        #通常時値は入れない
        self.selected_iid = ''

    def insert_subtree(self, parent_iid, subtrees):
        #insertした際にiidが変更されるため，その対応リストを作成
        iid_correspondence_list = []

        for node in subtrees:
            new_parent_iid = parent_iid
            for iid_correspondence in iid_correspondence_list:
                if iid_correspondence[0] == node[4]:
                    new_parent_iid = iid_correspondence[1]

            iid = self.add_node(
                parent_iid=new_parent_iid, 
                nodename=node[1], 
                nodetype=node[2], 
                operator=node[3],
                log='insert subtree',
                is_reset_fig=False
                )

            iid_correspondence_list.append((node[0],iid))

        #再描画
        self.reset_fig(is_reset_graph=False, is_add_history=True)

    def move_outlineitem_down(self, event=None):
        #ショートカットからだと選択変更イベントを意図的に発生させる
        reselect_is = True

        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
            if self.selected_iid == '':return 0
        else:
            reselect_is = False

        parent_iid = self.outliner.parent(self.selected_iid)
        if parent_iid == '':return 0

        item_index = self.outliner.index(self.selected_iid)
        if item_index < len(self.outliner.get_children(parent_iid)) - 1:
            item_index += 1
            self.outliner.move(self.selected_iid, parent_iid, item_index)

            #選択変更イベントを発生させる
            if reselect_is == True:self.outliner.selection_set(self.selected_iid)

            log = 'down'
            nodename=self.outliner.item(self.selected_iid,'text')
            nodetype=self.outliner.item(self.selected_iid,'tags')[0]
            operator=self.outliner.item(self.selected_iid,'tags')[1]

            #log出力
            self.output_log('sort', log, self.selected_iid, nodename, nodetype, operator, parent_iid)

        #通常時値は入れない
        self.selected_iid = ''

    def move_outlineitem_up(self, event=None):
        #ショートカットからだと選択変更イベントを意図的に発生させる
        reselect_is = True

        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
            if self.selected_iid == '':return 0
        else:
            reselect_is = False

        parent_iid = self.outliner.parent(self.selected_iid)
        if parent_iid == '':return 0

        item_index = self.outliner.index(self.selected_iid)
        if item_index >= 1:
            item_index -= 1
            self.outliner.move(self.selected_iid, parent_iid, item_index)

            #選択変更イベントを発生させる
            if reselect_is == True:self.outliner.selection_set(self.selected_iid)

            log = 'up'
            nodename=self.outliner.item(self.selected_iid,'text')
            nodetype=self.outliner.item(self.selected_iid,'tags')[0]
            operator=self.outliner.item(self.selected_iid,'tags')[1]

            #log出力
            self.output_log('sort', log, self.selected_iid, nodename, nodetype, operator, parent_iid)

        #通常時値は入れない
        self.selected_iid = ''

    def notify_test_is_complete(self):
        messagebox.showinfo('infomation', 'お疲れ様でした。検証は終了です。' + '\n' + '現時点を保存してアプリを終了してください。')

    def outlineitem_close(self, event=None):
        self.reset_fig(is_reset_graph=True, is_add_history=False)

    def outlineitem_open(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
        if self.selected_iid == '':return 0

        self.reset_fig(is_reset_graph=True, is_add_history=False, parent_iid='', protected_iid=self.selected_iid)

        #通常時値は入れない
        self.selected_iid = ''

    def outlineitem_select(self, event=None):
        #コンテキストメニューが開かれていればスキップ
        if self.selected_iid != '':
            return 0
        else:
            if len(self.outliner.selection()) == 0:
                self.attention_iid = ''
            else:
                self.attention_iid = self.outliner.selection()[0]

        self.reset_fig(is_reset_graph=True, is_add_history=False)

    def output_fig(self, output_dpi, event=None):
        fig_path = ''
        fig_name = 'attacktrees'
        fig_fullname = fig_name + '.png'
        num = 1

        #重複確認
        while os.path.isfile(self.fig_output_dir.joinpath(fig_fullname)):
            fig_name = 'attacktrees_' + str(num)
            fig_fullname = fig_name + '.png'
            num += 1

        #ダイアログ
        fig_path = filedialog.asksaveasfilename(
            title = '画像出力', filetypes = [('PNG', '.png')], initialfile = fig_name,
            initialdir = self.fig_output_dir, defaultextension = 'png'
        )
        
        #レンダリングのため拡張子を除去
        if fig_path != '':
            figdir = os.path.dirname(fig_path)
            fig_name = os.path.splitext(os.path.basename(fig_path))[0]
            render_path = os.path.join(figdir, fig_name)

            self.graph.attr('graph', dpi=output_dpi)
            self.graph.render(render_path, cleanup=True)
            self.graph.attr('graph', dpi=str(self.fig_dpi))

        #出力確認
        if os.path.isfile(fig_path):
            messagebox.showinfo('infomation', '正常に出力されました．\n['+str(fig_path)+']')
        else:
            messagebox.showinfo('infomation', '出力されませんでした．')

    def output_log(self, operation, detail, iid, nodename, nodetype, operator, parent_iid):
        with open(self.log_filepath, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.datetime.now(), operation, detail, iid, nodename, 
                nodetype, operator, parent_iid, self.output_filename, self.uuid
                ])

        print(
            datetime.datetime.now(), operation, detail, iid, nodename, 
            nodetype, operator, parent_iid, self.output_filename, self.uuid
            )

    def pack_widgets(self):
        self.pack()
        self.panedwindow_main.pack(expand=True, fill = tk.BOTH, side="left")
        self.panedwindow_main.add(self.panedwindow_left)
        self.panedwindow_main.add(self.panedwindow_right)
        self.attackcanvas.place(x=0, y=0)
        self.canvas_xbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas_ybar.pack(side=tk.RIGHT, fill=tk.Y)
        self.outliner_xbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.outliner_ybar.pack(side=tk.RIGHT, fill=tk.Y)
        self.outliner.pack(expand=True, fill=tk.X)

    def partsview_state_is(self):
        state_is = 'None'

        if self.partsview is not None:
            try:self.partsview.winfo_exists()
            except Exception as e:print(e)

            if self.partsview.winfo_exists():
                state_is = 'Open'
            else:
                state_is = 'Close'

        return state_is

    def paste_subtrees(self, event=None):
        #コンテキストメニューからの呼び出しでは事前にiid取得しておく
        if self.selected_iid == '':
            self.selected_iid = self.outliner.focus()
        if self.selected_iid == '':return 0

        subtrees = self.clipboard_get()

        try:
            subtrees = eval(subtrees)
        except Exception as e:
            print(e)
            return 0

        #[(#,#,#),...]の形になっているか確認　　
        if not isinstance(subtrees, list):return 0
        for node in subtrees:
            if not isinstance(node, tuple):return 0
            if len(node) != 5:return 0

        self.insert_subtree(self.selected_iid, subtrees)

        #通常時値は入れない
        self.selected_iid = ''

    def read_file(self, event=None):
        if self.index_now != self.index_saved:
            if messagebox.askyesno(title='保存確認', message='変更を保存しますか？'):
                self.save()
        
        close_filename = self.output_filename
        attacktrees_xml = self.get_inputfile()
        if not attacktrees_xml is None:
            self.output_log('close', 'close file ' + close_filename, '', '', '', '', '')
            self.output_log('open', 'open file ' + self.output_filename, '', '', '', '', '')
            self.reset_outliner(attacktrees_xml)
            self.reset_fig(is_reset_graph=True, is_add_history=False)
            self.update_history_on_readfile()

        self.focus()
        self.outliner.selection_set(self.outliner.get_children()[0])
        self.outliner.focus(self.outliner.get_children()[0])

    def reconsttuction(self, parent_iid='', protected_iid=''):
        #再帰処理
        child_iid_tuple = self.outliner.get_children(parent_iid)
        for child_iid in child_iid_tuple:
            nodename = self.outliner.item(child_iid,'text')
            nodetype = self.outliner.item(child_iid,'tags')[0]
            operator = self.outliner.item(child_iid,'tags')[1]

            #nodeの追加
            if nodetype == 'pattern':
                if child_iid == self.attention_iid:
                    pencolor = self.pencolor_attention
                    penwidth = self.penwidth_attention
                else:
                    pencolor = self.pencolor_pattern
                    penwidth = self.penwidth_pattern

                self.graph.node(
                    child_iid, 
                    nodename, 
                    color=pencolor,
                    fontname=self.fontname_pattern,
                    fontcolor=self.fontcolor_pattern, 
                    style=self.style_pattern, 
                    fillcolor=self.fillcolor_pattern,
                    penwidth=penwidth
                    )
            elif nodetype == 'free':
                if child_iid == self.attention_iid:
                    pencolor = self.pencolor_attention
                    penwidth = self.penwidth_attention
                else:
                    pencolor = self.pencolor_free
                    penwidth = self.penwidth_free

                self.graph.node(
                    child_iid, 
                    nodename, 
                    color=pencolor,
                    fontname=self.fontname_free,
                    fontcolor=self.fontcolor_free, 
                    style=self.style_free, 
                    fillcolor=self.fillcolor_free,
                    penwidth=penwidth
                    )
            else:
                print('ERROR on reconstruction : [' + repr(nodetype) + '] tag is not specified.')

            #top nodeじゃなければedge追加
            if not parent_iid == '':
                if operator == 'or':self.graph.edge(parent_iid,child_iid, arrowtail='normal')
                elif operator == 'and':self.graph.edge(parent_iid,child_iid, arrowtail='onormal')
                else:print('ERROR on reconstruction : [' + repr(operator) + '] operator is not specified.')

            #protected_iid:<<TreeviewOpen>>から呼ばれた時にツリーが展開しているのにopen=Falseになってしまうための対策
            if child_iid == protected_iid or self.outliner.item(child_iid,'open') == True:
                child_iid_tuple += self.reconsttuction(parent_iid=child_iid, protected_iid=protected_iid)

        return child_iid_tuple

    def redo(self, event=None):
        if self.index_now < len(self.history_stack) - 1:
            self.index_now += 1
            self.reset_outliner(self.history_stack[self.index_now])
            self.reset_fig(is_reset_graph=True, is_add_history=False)
            self.reset_title()

            #log出力
            self.output_log('redo', 'redo', '', '', '', '', '')

    def release_selection(self, event=None):
        #コンテキストメニューが開かれていればスキップ
        if self.selected_iid != '':return 0
        else:self.attention_iid = ''

        self.outliner.selection_set('')
        self.outliner.focus('')

    def reset_fig(self, is_reset_graph, is_add_history, parent_iid='', protected_iid=''):
        if is_reset_graph == True:
            self.graph.clear()
            self.set_graph_attr()
            self.reconsttuction(parent_iid, protected_iid)

        if is_add_history == True:
            self.add_history()

        self.update_fig()

    def reset_outliner(self, attacktrees_xml):
        #全てのtreeview itemを削除
        self.outliner.delete(*self.outliner.get_children())

        log = 'read from ' + self.output_filename
        at_root = attacktrees_xml.getroot()
        for attack_trees in at_root.iter('AttackTrees'):
            for infomation in attack_trees.iter('Information'):
                self.uuid = infomation.attrib['UUID']

            for nodes in attack_trees.iter('Nodes'):
                for node in nodes.iter('Node'):
                    iid = node.attrib['ID']
                    nodename = node.attrib['Name']
                    nodetype = node.attrib['Type']
                    operator = node.attrib['Operator']
                    parent_id = node.attrib['ParentID']
                    nodename = self.arrenge_nodename(nodename)
                    self.outliner.insert(
                        parent=parent_id, iid=iid, index='end',
                        text=nodename, tags=(nodetype,operator),open="True")

                    self.output_log('add', log, iid, nodename, nodetype, operator, parent_id)

    def reset_title(self):
        if self.output_filename != '':
            if self.index_now == self.index_saved:
                self.master.title(self.output_filename)
            else:
                self.master.title('[編集中]' + self.output_filename)

    def resize_canvas(self, new_width, new_height):
        self.canvas_width = new_width
        self.canvas_height = new_height
        self.canvas_scrollregion =(self.canvas_width*(-2), self.canvas_height*(-2), self.canvas_width*4, self.canvas_height*4)
        self.attackcanvas.config(width=new_width)
        self.attackcanvas.config(height=new_height)
        self.attackcanvas.config(scrollregion=self.canvas_scrollregion)

    def resize_panedright(self, event):
        self.resize_canvas(event.width, event.height)
        self.window_width = event.width
        self.window_height = event.height

    def save(self, show_message=True, event=None):
        #新規作成の場合は，save_asへ飛ばす
        if self.output_filename == '':
            self.save_as()
            return ''

        output_path = os.path.join(self.output_dir, self.output_filename)

        self.create_output()
        with open(output_path, 'wb') as output:
            self.output_xml.write(output, encoding='UTF-8', xml_declaration=True)

        self.update_history_on_save()
        if show_message == True:messagebox.showinfo('infomation', '変更を保存しました．')

        self.output_log('save', 'save', '', '', '', '', '')

    def save_as(self, event=None):
        #ファイル名の候補を生成
        initial_filename = ''
        if self.output_filename == '':
            childeren = self.outliner.get_children()
            for child in childeren:
                initial_filename += self.outliner.item(child,'text')
        else:
            initial_filename = os.path.basename(self.output_filename)

#        self.master.unbind_all()

        filename = filedialog.asksaveasfilename(
            title = "名前を付けて保存",
            filetypes = [('XML', ".xml")],
            initialdir = self.output_dir,
            initialfile = initial_filename,
            defaultextension = "xml"
        )

        if filename == '': return 0

        self.output_filename = filename
        self.output_dir = os.path.dirname(filename)
        self.create_output()
        with open(filename, 'wb') as output:
            self.output_xml.write(output, encoding='UTF-8', xml_declaration=True)

        self.update_history_on_save()

        self.output_log('save', 'save as ' + self.output_filename, '', '', '', '', '')

    def set_config(self):
        self.config_ini = configparser.ConfigParser()
        self.config_ini.read(self.config_path)

    def set_dirs(self):
        if self.os_name == 'Windows':
            parent_dir_path = '~\AppData\Local\Programs'
            fig_output_dir_path = '~\Downloads'

        if self.os_name == 'Mac':
            parent_dir_path = '~/Library'
            fig_output_dir_path = '~/Downloads'

        self.parent_dir = Path(os.path.expanduser(parent_dir_path))
        self.rattata_dir = self.parent_dir.joinpath('RATTATA')
        self.data_dir = self.rattata_dir.joinpath('data')
        self.output_dir = self.data_dir.joinpath('output')
        self.fig_dir = self.data_dir.joinpath('fig')
        self.log_dir = self.data_dir.joinpath('log')
        self.capec_dir = self.data_dir.joinpath('capec')
        self.fig_output_dir = Path(os.path.expanduser(fig_output_dir_path))

        if not os.path.isdir(self.rattata_dir):os.mkdir(self.rattata_dir)
        if not os.path.isdir(self.data_dir):os.mkdir(self.data_dir)
        if not os.path.isdir(self.output_dir):os.mkdir(self.output_dir)
        if not os.path.isdir(self.fig_dir):os.mkdir(self.fig_dir)
        if not os.path.isdir(self.log_dir):os.mkdir(self.log_dir)
        if not os.path.isdir(self.capec_dir):os.mkdir(self.capec_dir)

    def set_events(self):
        if self.os_name == 'Windows':
            modifier_key = 'Control'
            rightclick_key = 'Button-3'

        if self.os_name == 'Mac':
            modifier_key = 'Command'
            rightclick_key = 'Button-2'

        self.master.bind('<BackSpace>', self.delete_selection)
        self.master.bind('<'+modifier_key+'-KeyPress-c>', self.copy_subtrees)
        self.master.bind('<'+modifier_key+'-KeyPress-d>', self.move_outlineitem_down)
        self.master.bind('<'+modifier_key+'-KeyPress-e>', self.change_selection)
        self.master.bind('<'+modifier_key+'-KeyPress-minus>', self.decrease_dpi)
        self.master.bind('<'+modifier_key+'-KeyPress-o>', self.read_file)
        self.master.bind('<'+modifier_key+'-KeyPress-p>', self.output_fig)
        self.master.bind('<'+modifier_key+'-KeyPress-plus>', self.increase_dpi)
        self.master.bind('<'+modifier_key+'-KeyPress-r>', self.show_partsview)
        self.master.bind('<'+modifier_key+'-KeyPress-s>', self.save)
        self.master.bind('<'+modifier_key+'-KeyPress-u>', self.move_outlineitem_up)
        self.master.bind('<'+modifier_key+'-KeyPress-v>', self.paste_subtrees)
        self.master.bind('<'+modifier_key+'-KeyPress-x>', self.cut_subtrees)
        self.master.bind('<'+modifier_key+'-KeyPress-z>', self.undo)
        self.master.bind('<'+modifier_key+'-Shift-KeyPress-Z>', self.redo)
        self.master.bind('<'+modifier_key+'-Shift-KeyPress-S>', self.save_as)
        self.master.bind('<Return>', self.insert_child)
        self.master.bind('<Tab>', self.insert_brother)
        self.master.bind('<Escape>', self.release_selection)
        self.master.protocol("WM_DELETE_WINDOW", self.close_window)

        self.attackcanvas.tag_bind('img', '<ButtonPress-1>', self.image_pressed)
        self.attackcanvas.tag_bind('img', '<B1-Motion>', self.image_dragged)

        self.panedwindow_right.bind('<Configure>', self.resize_panedright)

        self.outliner.bind('<'+rightclick_key+'>', self.show_contextmenu)
        self.outliner.bind('<<TreeviewOpen>>', self.outlineitem_open)
        self.outliner.bind('<<TreeviewClose>>', self.outlineitem_close)
        self.outliner.bind('<<TreeviewSelect>>', self.outlineitem_select)

    def set_files(self):
        self.fig_file_name = self.config_ini.get(self.config_section_name, 'figname_on_render')
        self.output_filename = ''
        self.log_filename = self.config_ini.get(self.config_section_name, 'log_filename')

    def set_graph_attr(self):
        self.fontname_free = self.config_ini.get(self.config_section_name, 'fontname_of_freenode')
        self.pencolor_free = self.config_ini.get(self.config_section_name, 'color_of_freenode')
        self.fontcolor_free = self.config_ini.get(self.config_section_name, 'fontcolor_of_freenode')
        self.fillcolor_free = self.config_ini.get(self.config_section_name, 'fillcolor_of_freenode')
        self.style_free = self.config_ini.get(self.config_section_name, 'style_of_freenode')
        self.penwidth_free = self.config_ini.get(self.config_section_name, 'penwidth_of_freenode')

        self.fontname_pattern = self.config_ini.get(self.config_section_name, 'fontname_of_patternnode')
        self.fontcolor_pattern = self.config_ini.get(self.config_section_name, 'fontcolor_of_patternnode')
        self.pencolor_pattern = self.config_ini.get(self.config_section_name, 'color_of_patternnode')
        self.fillcolor_pattern = self.config_ini.get(self.config_section_name, 'fillcolor_of_patternnode')
        self.style_pattern = self.config_ini.get(self.config_section_name, 'style_of_patternnode')
        self.penwidth_pattern = self.config_ini.get(self.config_section_name, 'penwidth_of_patternnode')

        self.penwidth_attention = self.config_ini.get(self.config_section_name, 'penwidth_of_attentionnode')
        self.pencolor_attention = self.config_ini.get(self.config_section_name, 'color_of_attentionnode')

        self.node_shape = self.config_ini.get(self.config_section_name, 'node_shape')
        self.edge_direction = self.config_ini.get(self.config_section_name, 'edge_direction')
        self.arrowhead = self.config_ini.get(self.config_section_name, 'arrowhead')
        self.arrowtail = self.config_ini.get(self.config_section_name, 'arrowtail')

        self.graph = Digraph(format='png')
        self.graph.attr('graph', dpi=str(self.fig_dpi))
        self.graph.attr('node',shape=self.node_shape)
        self.graph.attr('edge', dir=self.edge_direction, arrowhead=self.arrowhead, arrowtail=self.arrowtail)

    def set_history(self):
        self.history_stack = []
        self.index_saved = -1
        self.index_now = -1
        self.add_history()
        self.index_saved = self.index_now

    def set_objects(self, master):
        self.master = master
        self.attackcanvas = None
        self.attackimage_raw = None
        self.attackimage_tk = None
        self.canvas_xbar = None
        self.canvas_ybar = None
        self.outliner_xbar = None
        self.outliner_ybar = None
        self.graph = None
        self.panedwindow_main = None
        self.panedwindow_left = None
        self.panedwindow_right = None
        self.manubar = None
        self.contextmenu = None
        self.outliner = None
        self.output_xml = None
        self.input_window = None
        self.partsview = None
        self.tutorial_win_1 = None
        self.tutorial_win_2 = None

    def set_os(self):
        self.os_name = ''
        self.config_section_name = ''
        if platform.system() == 'Windows' :
            self.os_name = 'Windows'
            self.config_section_name = 'WINDOWS'
        elif platform.system() == 'Darwin':
            self.os_name = 'Mac'
            self.config_section_name = 'MACOS'
        elif platform.system() == 'Linux' :
            self.os_name = 'Linux'
            self.config_section_name = 'DEFAULT'
        else:
            self.os_name = 'other'
            self.config_section_name = 'DEFAULT'

        if self.os_name == 'Linux':
            messagebox.showerror('Error on set_os', 'RATTATAはLinux非対応です')
            sys.exit()

        if self.os_name == 'other':
            messagebox.showerror('Error on set_os', '非対応のOSです')
            sys.exit()

    def set_mode(self):
        self.is_automatic_lfcode_insertion = False
        self.is_configfile_updatable = False

    def set_sizes(self):
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()

        self.window_ratio = float(self.config_ini.get(self.config_section_name, 'ratio_between_size_of_window_to_screen'))
        self.window_width = int(self.screen_width * self.window_ratio)
        self.window_height = int(self.screen_height * self.window_ratio)

        self.panedborder_width = int(self.config_ini.get(self.config_section_name, 'border_width_of_panedwindow'))
        self.panedwindow_ratio = float(self.config_ini.get(self.config_section_name, 'ratio_between_width_of_panedleft_to_window'))
        self.panedleft_width = int(self.window_width * self.panedwindow_ratio)
        self.panedright_width = self.window_width - self.panedleft_width - self.panedborder_width

        self.canvas_width = self.panedright_width
        self.canvas_height = self.window_height
        self.canvas_scrollregion =(
            self.canvas_width*(-0.1), self.canvas_height*(-0.1), 
            self.canvas_width*1.2, self.canvas_height*1.2)

        self.img_x = self.canvas_width/2
        self.img_y = 0

        self.fig_dpi = self.config_ini.get(self.config_section_name, 'figdpi')
        self.nodename_length = int(self.config_ini.get(self.config_section_name, 'length_per_line_of_nodename'))

        self.inputwin_width = int(self.config_ini.get(self.config_section_name, 'inputwindow_width'))
        self.inputwin_height = int(self.config_ini.get(self.config_section_name, 'inputwindow_height'))

        self.tutorialwin_width = int(self.config_ini.get(self.config_section_name, 'tutorial_window_width'))
        self.tutorialwin_height = int(self.config_ini.get(self.config_section_name, 'tutorial_window_height'))

    def set_temporary_values(self):
        self.attention_iid = ''
        self.selected_iid = ''
        self.input_text = ''

    def set_uuid(self):
        self.uuid = uuid.uuid4()

    def set_window_geometry(self):
        self.master.geometry(
            str(self.window_width) + 'x' + 
            str(self.window_height) + '+' + 
            str(int(self.screen_width/2-self.window_width/2)) + '+' + 
            str(int(self.screen_height/2-self.window_height/2)))

    def show_contextmenu(self, event):
        self.selected_iid = self.outliner.identify_row(event.y)
        if self.selected_iid != '':
            self.outliner.selection_set(self.selected_iid)
            self.contextmenu.post(event.x_root, event.y_root)

        #通常時値は入れない
        self.selected_iid = ''

    def show_partsview(self, event=None): 
        if self.partsview_state_is() == 'None' or self.partsview_state_is == 'Close':
            if self.inputwindow_state_is() == 'Open':self.input_window.destroy()
            self.partsview = PartsView.PartsView(self.master, self)
            self.partsview.title('パーツ検索')
            self.partsview.focus_set()
        elif self.partsview_state_is() == 'Open':
            self.partsview.focus_set()

    def show_tutorial(self):
        if self.is_configfile_updatable == False:return 0
        time.sleep(1)
        self.tutorial_1()
        self.master.wait_window(self.tutorial_win_1)

        self.tutorial_2()
        self.master.wait_window(self.tutorial_win_2)

        messagebox.showinfo('infomation', 'これでチュートリアルは終了です．' + '\n' + 'チュートリアルは上部のメニューバーから再確認できます．')

        self.focus_force()
        self.outliner.selection_set(self.outliner.get_children()[0])
        self.outliner.focus(self.outliner.get_children()[0])

    def tutorial_1(self):
        #サブウィンドウ生成
        self.tutorial_win_1 = tk.Toplevel()
        self.tutorial_win_1.title('チュートリアル 1')
        self.tutorial_win_1.geometry(
            str(self.tutorialwin_width) + 'x' + 
            str(self.tutorialwin_height) + '+' + 
            str(int(self.screen_width/2 - self.tutorialwin_width/2)) + '+' + 
            str(int(self.screen_height/2 - self.tutorialwin_height/2)))
        
        #モーダルモード
        self.tutorial_win_1.grab_set()
        self.tutorial_win_1.focus_set()

        font_title = font.Font(family=self.fontname_free, weight='bold', size='30')
        font_head = font.Font(family=self.fontname_free, size='25')
        font_text = font.Font(family=self.fontname_free, size='15')

        title = tk.Label(self.tutorial_win_1, text='アタックツリーを作ろう', font=font_title)
        head_1 = tk.Label(self.tutorial_win_1, text='アウトライン（画面左側）操作', font=font_head, )
        text_1_1 = tk.Label(self.tutorial_win_1, text=' - [Enter] : 子ノードを作成', font=font_text)
        text_1_2 = tk.Label(self.tutorial_win_1, text=' - [Tab] : 兄弟ノードを作成', font=font_text)
        text_1_3 = tk.Label(self.tutorial_win_1, text=' - [ダブルクリック] : ノードの編集', font=font_text)
        text_1_4 = tk.Label(self.tutorial_win_1, text=' - [delete] : ノードの削除', font=font_text)

        head_2 = tk.Label(self.tutorial_win_1, text='キャンバス（画面右側）操作', font=font_head)
        text_2_1 = tk.Label(self.tutorial_win_1, text=' - [ドラッグ] : ツリーの移動', font=font_text)

        head_3 = tk.Label(self.tutorial_win_1, text='その他', font=font_head)
        text_3_1 = tk.Label(self.tutorial_win_1, text='細かいのは画面上部のメニューバーや右クリックメニューから', font=font_text)
        text_3_2 = tk.Label(self.tutorial_win_1, text='ショートカットコマンドはメニューの右から確認しよう', font=font_text)

        button = tk.Button(self.tutorial_win_1, text='やってみる')

        def ok_click(event=None):self.tutorial_win_1.destroy()
        def close_click():self.input_window.destroy()

        self.tutorial_win_1.protocol('WM_DELETE_WINDOW', close_click)
        self.tutorial_win_1.bind('<Key-Return>', ok_click)
        button['command'] = ok_click

        title.pack(side=tk.TOP, anchor=tk.CENTER)
        head_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=10)
        text_1_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_1_2.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_1_3.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_1_4.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        head_2.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=10)
        text_2_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        head_3.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=10)
        text_3_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_3_2.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        button.pack(side=tk.TOP, anchor=tk.CENTER, pady=20)

        button.focus_set()

    def tutorial_2(self):
        #サブウィンドウ生成
        self.tutorial_win_2 = tk.Toplevel()
        self.tutorial_win_2.title('チュートリアル 2')
        self.tutorial_win_2.geometry(
            str(self.tutorialwin_width) + 'x' + 
            str(self.tutorialwin_height) + '+' + 
            str(int(self.screen_width/2 - self.tutorialwin_width/2)) + '+' + 
            str(int(self.screen_height/2 - self.tutorialwin_height/2)))
        
        #モーダルモード
        self.tutorial_win_2.grab_set()
        self.tutorial_win_2.focus_set()

        font_title = font.Font(family=self.fontname_free, weight='bold', size='30')
        font_head = font.Font(family=self.fontname_free, size='25')
        font_text = font.Font(family=self.fontname_free, size='15')

        title = tk.Label(self.tutorial_win_2, text='パーツを再利用しよう', font=font_title)
        head_1 = tk.Label(self.tutorial_win_2, text='パーツ検索ビューを表示する', font=font_head, )
        text_1_1 = tk.Label(self.tutorial_win_2, text=' - 上部のメニューバーから[再利用]-[パーツ検索ビューを表示]', font=font_text)

        head_2 = tk.Label(self.tutorial_win_2, text='パーツを検索する', font=font_head)
        text_2_1 = tk.Label(self.tutorial_win_2, text=' - [他のツリーから検索] もしくは [CAPECから検索]を選択', font=font_text)
        text_2_2 = tk.Label(self.tutorial_win_2, text=' - 検索バーにキーワードを入力して[検索]', font=font_text)
        text_2_3 = tk.Label(self.tutorial_win_2, text=' - キーワードを入力しない場合全件検索になります', font=font_text)

        head_3 = tk.Label(self.tutorial_win_2, text='パーツを使用する', font=font_head)
        text_3_1 = tk.Label(self.tutorial_win_2, text=' - 検索結果から使用したいパターンをクリック', font=font_text)
        text_3_2 = tk.Label(self.tutorial_win_2, text=' - パーツのレビュー画面上でダブルクリックするとコピーされます', font=font_text)
        text_3_3 = tk.Label(self.tutorial_win_2, text=' - 元の画面に戻って接続したい親ノードに[ペースト]', font=font_text)

        button = tk.Button(self.tutorial_win_2, text='やってみる')

        def ok_click(event=None):self.tutorial_win_2.destroy()
        def close_click():self.input_window.destroy()

        self.tutorial_win_2.protocol('WM_DELETE_WINDOW', close_click)
        self.tutorial_win_2.bind('<Key-Return>', ok_click)
        button['command'] = ok_click

        title.pack(side=tk.TOP, anchor=tk.CENTER)
        head_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=10)
        text_1_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        head_2.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=10)
        text_2_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_2_2.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_2_3.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        head_3.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=10)
        text_3_1.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_3_2.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        text_3_3.pack(side=tk.TOP, anchor=tk.W, padx=20, pady=2)
        button.pack(side=tk.TOP, anchor=tk.CENTER, pady=20)

        button.focus_set()

    def undo(self, event=None):
        if self.index_now > 0:
            self.index_now -= 1
            self.reset_outliner(self.history_stack[self.index_now])
            self.reset_fig(is_reset_graph=True, is_add_history=False)
            self.reset_title()

            #log出力
            self.output_log('undo', 'undo', '', '', '', '', '')

    def update_fig(self):
        #pngファイル出力
        fig_body = Path(self.fig_file_name).stem

        try:
            self.graph.render(os.path.join(self.fig_dir, fig_body))
        except Exception as e:
            messagebox.askokcancel('Exception', e)

        #pngファイル読み込み
        fig_path = os.path.join(self.fig_dir, self.fig_file_name)
        self.attackimage_raw = Image.open(fig_path)
        self.expand_canvas()
        self.attackimage_tk = ImageTk.PhotoImage(self.attackimage_raw)
        self.attackcanvas.create_image(
            self.img_x, self.img_y, image=self.attackimage_tk, anchor='n', tags='img')

    def update_history_on_readfile(self):
        self.set_history()
        self.index_saved = self.index_now
        self.reset_title()

    def update_history_on_save(self):
        self.index_saved = self.index_now
        self.reset_title()
