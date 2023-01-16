from graphviz import Digraph
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import ttk
from tkinter import messagebox
import configparser
import glob
import operator
import os
import textwrap
import tkinter as tk
import xml.etree.ElementTree as ET



class PartsView(tk.Toplevel):
    def __init__(self, master=None, mainwindow=None):
        super().__init__(master)
        self.mainwindow = mainwindow
        self.share_values_from_mainwindow()
        self.set_config()
        self.set_sizes()
        self.set_window_geometry()
        self.init_objects()
        self.create_frame()
        self.create_widgets_onleft()
        self.create_canvas()
        self.create_reuse_conditions()
        self.create_scrollbar()
        self.pack_widgets()
        self.load_capec()
        self.set_graph()
        self.set_files()
        self.set_events()

    def add_conditions(self, condition):
        self.reuse_conditions.insert(tk.END, condition)

    def add_label_oncanvas(self, event):
        if self.listview.focus() == '':return 0
        self.label_oncanvas = tk.Label(
            self.partscanvas, 
            text='ダブルクリックでコピー', 
            font=('',20),
            bg='white',
            foreground='black',
            anchor=tk.NW, 
            justify='left')
        self.label_oncanvas.place(x=20,y=20)

    def add_list(self, parent_iid, text, is_open, type='', operator=''):
        child_iid = self.listview.insert(
            parent=parent_iid, index='end', text=text, tags=(type,operator), open=is_open
            )
        return child_iid

    def add_subtree_tograph(self, subtree, parent_iid=''):
        node_iid = subtree[0]
        node_name = self.listview.item(node_iid, 'text')
        self.graph.node(
            node_iid, node_name, fontname=self.fontname_pattern,
            fontcolor=self.fontcolor_pattern, style=self.style_pattern, 
            fillcolor=self.fillcolor_pattern, penwidth=self.penwidth_pattern)

        for childnode_iid in subtree[1]:
            childnode_name = self.listview.item(childnode_iid, 'text')
            self.graph.node(
                childnode_iid, childnode_name, fontname=self.fontname_pattern,
                fontcolor=self.fontcolor_pattern, style=self.style_pattern, 
                fillcolor=self.fillcolor_pattern, penwidth=self.penwidth_pattern)

            self.graph.edge(node_iid, childnode_iid, arrowtail='onormal')

        if parent_iid != '':
            parent_name = self.listview.item(parent_iid, 'text')
            self.graph.node(
                parent_iid, parent_name, fontname=self.fontname_free,
                fontcolor=self.fontcolor_free, style=self.style_free, 
                fillcolor=self.fillcolor_free, penwidth=self.penwidth_free)
            self.graph.edge(parent_iid, node_iid, arrowtail='normal')

    def copy_parts(self, event=None):
        selected_iid = self.listview.focus()
        if selected_iid == '':return 0

        ancestor_iid = self.get_ancestor(selected_iid)
        parts_tuple = self.get_parts(ancestor_iid)

        subtrees = []

        iid = parts_tuple[0]
        nodename = self.listview.item(iid, 'text')
        nodetype = 'pattern'
        operator = 'or'
        parent_iid = self.listview.parent(iid)
        subtrees.append((iid, nodename, nodetype, operator, parent_iid))

        log = 'copy pattern ' + parts_tuple[2] + ' ' + parts_tuple[3]
        self.mainwindow.output_log('copy', log, iid, nodename, nodetype, operator, parent_iid)

        for iid in parts_tuple[1]:
            nodename = self.listview.item(iid, 'text')
            nodetype = 'pattern'
            operator = 'and'
            parent_iid = self.listview.parent(iid)
            subtrees.append((iid, nodename, nodetype, operator, parent_iid))
    
            self.mainwindow.output_log('copy', log, iid, nodename, nodetype, operator, parent_iid)

        self.clipboard_clear()
        self.clipboard_append(repr(subtrees))

        self.label_oncanvas.config(text='コピーされました')

    def create_reuse_conditions(self):
        font_size = self.config_ini.get(self.config_section_name, 'fontsize_of_reuseconditions')
        self.reuse_conditions = tk.Text(self.frame_bottomright, font=('', font_size))

    def create_scrollbar(self):        
        self.listview_xbar = tk.Scrollbar(self.frame_listview, orient=tk.HORIZONTAL)
        self.listview_ybar = tk.Scrollbar(self.frame_listview, orient=tk.VERTICAL)
        self.listview_xbar.config(command=self.listview.xview)
        self.listview_ybar.config(command=self.listview.yview)
        self.listview.config(xscrollcommand=self.listview_xbar.set)
        self.listview.config(yscrollcommand=self.listview_ybar.set)

    def create_widgets_onleft(self):
        self.radiovar = tk.IntVar()
        self.radiovar.set(0)
        self.radio_reuse = tk.Radiobutton(
            self.frame_radio, value=0, variable=self.radiovar, text='他のツリーから検索')
        self.radio_capec = tk.Radiobutton(
            self.frame_radio, value=1, variable=self.radiovar, text='CAPECから検索')

        self.entry_keyword = tk.Entry(
            self.frame_search, justify=tk.LEFT, textvariable=self.entry_keyword)
        self.button_serach = tk.Button(
            self.frame_search, text='検索', command=self.serach_parts, width=self.searchbutton_width)

        self.listview = ttk.Treeview(self.frame_listview, height=300, show='tree')
        self.listview.column('#0', width=self.window_width)

    def create_canvas(self):
        self.partscanvas = tk.Canvas(self.frame_toprigth, width=self.canvas_width, height=self.canvas_height, bg='white')

    def create_frame(self):
        self.frame_left = ttk.Frame(
            self, width=self.frameleft_width, height=self.frameleft_height, padding=[20,20,20,20], relief=tk.FLAT)

        #サイズ固定
        self.frame_left.propagate(False)

        self.frame_radio = ttk.Frame(
            self.frame_left, width=self.frameradio_width, padding=[0,0,0,10], relief=tk.FLAT)

        self.frame_search = ttk.Frame(
            self.frame_left, width=self.framesearch_width, padding=[0,0,0,10], relief=tk.FLAT)

        self.frame_listview = ttk.Frame(
            self.frame_left, width=self.framelistview_width, padding=[3,0,3,0], relief=tk.FLAT)

        self.frame_toprigth = ttk.Frame(
            self, width=self.frametopright_width, height=self.frametopright_height, padding=[0,20,20,20], relief=tk.FLAT)

        self.frame_bottomright = ttk.Frame(
            self, width=self.framebottomright_width, height=self.framebottomright_height, padding=[3,0,23,20], relief=tk.FLAT)

    def delete_label_oncanvas(self, event):
        if self.label_oncanvas is not None:self.label_oncanvas.destroy()

    def get_ancestor(self, iid):
        parent_iid = self.listview.parent(iid)
        if parent_iid == '':
            return iid
        else:
            iid = self.get_ancestor(parent_iid)
            return iid

    def get_conditions(self, ancestor_iid):
        if self.listview.parent(ancestor_iid) != '':return 0
        condition_iid_list = []

        child_iid_list = self.listview.get_children(ancestor_iid)
        for child_iid in child_iid_list:
            if self.listview.item(child_iid,'text') == '適用条件':
                condition_iid_list = self.listview.get_children(child_iid)

        return condition_iid_list

    def get_rawconditions(self, ancestor_iid):
        if self.listview.parent(ancestor_iid) != '':return 0

        rawcondition_iid_list = []
        for child_iid in self.listview.get_children(ancestor_iid):
            if self.listview.item(child_iid,'text') == '原文':
                for class_iid in self.listview.get_children(child_iid):
                    for rawcodtion_iid in self.listview.get_children(class_iid):
                        rawcondition_iid_list.append(rawcodtion_iid)

        return rawcondition_iid_list

    def get_parts(self, ancestor_iid):
        if self.listview.parent(ancestor_iid) != '':return 0

        topnode_iid = ''
        bottomnode_list = []
        capec_id = ''
        filename = ''
        category_iid_list = self.listview.get_children(ancestor_iid)

        for category_iid in category_iid_list:
            if self.listview.item(category_iid,'text') == 'パーツ':
                topnode_iid = self.listview.get_children(category_iid)[0]
                bottomnode_list = self.listview.get_children(topnode_iid)

            if 'CAPEC ID : ' in self.listview.item(category_iid,'text'):
                capec_id = self.listview.item(category_iid,'text')

            if 'ファイル : ' in self.listview.item(category_iid,'text'):
                filename = self.listview.item(category_iid,'text')

        parts = (topnode_iid, bottomnode_list, capec_id, filename)
        return parts

    def get_parts_parent(self, ancestor_iid):
        if self.listview.parent(ancestor_iid) != '':return 0
        parts_parent_iid = ''

        child_iid_list = self.listview.get_children(ancestor_iid)
        for child_iid in child_iid_list:
            if self.listview.item(child_iid,'text') == '接続先':
                parts_parent_iid_list = self.listview.get_children(child_iid)
                if len(parts_parent_iid_list) != 0:
                    parts_parent_iid = parts_parent_iid_list[0]

        return parts_parent_iid

    def image_dragged(self, event):
        img_id = self.partscanvas.find_closest(event.x, event.y)
        delta_x = event.x - self.pre_x
        delta_y = event.y - self.pre_y

        self.img_x = self.img_x + delta_x
        self.img_y = self.img_y + delta_y
        self.partscanvas.coords(img_id, self.img_x, self.img_y)
        self.pre_x = event.x
        self.pre_y = event.y

    def image_pressed(self, event):
        self.pre_x = event.x
        self.pre_y = event.y

    def init_objects(self):
        self.frame_left = None
        self.frame_toprigth = None
        self.frame_bottomright = None
        self.radiovar = None
        self.radio_capec = None
        self.radio_reuse = None
        self.entry_keyword = None
        self.button_serach = None
        self.listview = None
        self.partscanvas = None
        self.reuse_conditions = None
        self.capec_tree = None
        self.partsimage_raw = None
        self.partsimage_tk = None
        self.partsimage = None
        self.label_oncanvas = None

    def load_capec(self):
        capec_filename = 'parts_list_from_capec.xml'
        capec_path = os.path.join(self.capec_dir, capec_filename)

        if not os.path.isfile(capec_path):
            messagebox.showerror('ERROR', capec_path + 'が見つかりません．')
            return 0

        self.capec_tree = ET.parse(capec_path)

    def search_parts_fromcapec(self, keyword):
        capec_root = self.capec_tree.getroot()
        keyword = keyword.lower()
        subset_list = []

        for patterns in capec_root.iter('Patterns'):
            for pattern in patterns.iter('Pattern'):
                #keywordを含まなければcontinue
                if not keyword in str(pattern.attrib['Name']).lower():continue

                id = pattern.attrib['ID']
                name = pattern.attrib['Name']
                ad_prereq_list = []
                ta_prereq_list = []
                parent_name = ''

                for prereqs in pattern.iter('Prerequisites'):
                    for prereq in prereqs.findall('Prerequisite'):
                        _class = prereq.attrib['Class']
                        for raw in prereq.iter('Raw'):raw_text = raw.text
                        for ja in prereq.iter('Japanese'):ja_text = ja.text

                        if _class == 'adversary':ad_prereq_list.append((raw_text, ja_text))
                        if _class == 'target':ta_prereq_list.append((raw_text, ja_text))

                parent_name = ''
                parts = (name, ad_prereq_list)
                filename = 'capec'
                subset_list.append(
                    (id, name, parts, ad_prereq_list, ta_prereq_list, parent_name, filename))

        return subset_list

    def search_reusable_parts(self, keyword):
        keyword = keyword.lower()

        #再利用するファイルを取得
        input_path = os.path.join(self.output_dir, '**/*.xml')
        input_files = glob.glob(input_path, recursive=True)

        #ファイル読み込み
        reuse_list = []
        for input_file in input_files:
            at_tree = ET.parse(input_file)
            at_root = at_tree.getroot()

            for attack_trees in at_root.iter('AttackTrees'):
                for nodes in attack_trees.iter('Nodes'):
                    for node_1 in nodes.iter('Node'):
                        if node_1.attrib['Type'] == 'pattern' and keyword in str(node_1.attrib['Name']).lower():
                            iid = node_1.attrib['ID']
                            name = node_1.attrib['Name']
                            parent_id = node_1.attrib['ParentID']
                            parent_name = ''
                            child_names = []

                            for node_2 in nodes.iter('Node'):
                                if parent_id == node_2.attrib['ID']:
                                    parent_name = node_2.attrib['Name']
                                if iid == node_2.attrib['ParentID'] and node_2.attrib['Type'] == 'pattern':
                                    child_names.append(('', node_2.attrib['Name']))

                            parent = parent_name
                            parts = (name, child_names)
                            reuse_list.append((name, parts, parent, input_file))

        #capecからパターンを検索する
        subset_list = []
        capec_list = self.search_parts_fromcapec('')
        for reuse in reuse_list:
            name_reuse = reuse[0]
            name_reuse = name_reuse.replace('\\n', '')
            name_reuse = name_reuse.replace('\\', '')
            name_reuse = name_reuse.replace(' ', '')

            for pattern in capec_list:
                name_pattern = pattern[1]
                name_pattern = name_pattern.replace('\\n', '')
                name_pattern = name_pattern.replace('\\', '')
                name_pattern = name_pattern.replace(' ', '')

                if name_reuse == name_pattern:
                    id = pattern[0]
                    name = pattern[1]
                    parts = reuse[1]
                    ad_prereq_list = pattern[3]
                    ta_prereq_list = pattern[4]
                    parent = reuse[2]
                    filename = reuse[3]
                    subset_list.append((
                        id, name, parts, ad_prereq_list, ta_prereq_list, parent, filename))

        return subset_list

    def serach_parts(self, event=None):
        self.listview.delete(*self.listview.get_children())
        keyword = self.entry_keyword.get()

        #ラジオボタンの取得
        if self.radiovar.get() == 0:subset_list = self.search_reusable_parts(keyword)
        if self.radiovar.get() == 1:subset_list = self.search_parts_fromcapec(keyword)

        #検索結果のソート
        subset_list = sorted(subset_list, key=operator.itemgetter(1))

        #listviewへの挿入
        for tuple in subset_list:
            id = tuple[0]
            name = tuple[1]
            parts = tuple[2]
            ad_prereq_list = tuple[3]
            ta_prereq_list = tuple[4]
            parent = tuple[5]
            filename = tuple[6]

            listview_id_root = self.add_list('', name, False)

            listview_id_capecid = self.add_list(listview_id_root, 'CAPEC ID : ' + id, True)
            listview_id_from = self.add_list(listview_id_root, 'ファイル : ' + filename, True)
            listview_id_parts = self.add_list(listview_id_root, 'パーツ', True)
            listview_id_conditions = self.add_list(listview_id_root, '適用条件', True)
            listview_id_parent = self.add_list(listview_id_root, '接続先', True)
            listview_id_raws = self.add_list(listview_id_root, '原文', True)
            listview_id_ad = self.add_list(listview_id_raws, '攻撃主体の条件', True)
            listview_id_ta = self.add_list(listview_id_raws, '攻撃対象の条件', True)

            if parent == '':
                #capecから作ったパーツは改行を入れる
                nodename = ' \\n '.join(textwrap.wrap(parts[0], width=20))
                listview_id_name = self.add_list(listview_id_parts, nodename, True, 'pattern')

                for childname in parts[1]:
                    childname_ja = ' \\n '.join(textwrap.wrap(childname[1], width=20))
                    listview_id_bottom = self.add_list(listview_id_name, childname_ja, True, 'pattern')
            else:
                #再利用したパーツは改行を改めて入れる必要はない
                listview_id_parentname = self.add_list(listview_id_parent, parent, True)
                nodename = parts[0]
                listview_id_name = self.add_list(listview_id_parts, nodename, True, 'pattern')

                for childname in parts[1]:
                    childname_ja = childname[1]
                    listview_id_bottom = self.add_list(listview_id_name, childname_ja, True, 'pattern')

            for ad_prereq in ad_prereq_list:
                listview_id_ad_raw = self.add_list(listview_id_ad, ad_prereq[0], True)
                listview_id_ad_ja = self.add_list(listview_id_ad_raw, ad_prereq[1], True)

            for ta_prereq in ta_prereq_list:
                listview_id_ta_raw = self.add_list(listview_id_ta, ta_prereq[0], True)
                listview_id_ta_ja = self.add_list(listview_id_ta_raw, ta_prereq[1], True)
                listview_id_condition = self.add_list(listview_id_conditions, ta_prereq[1], True)

    def set_sizes(self):
        self.window_ratio = float(self.config_ini.get(
            self.config_section_name, 
            'ratio_between_size_of_partview_window_to_screen'))
        self.window_width = int(self.screen_width * self.window_ratio)
        self.window_height = int(self.screen_height * self.window_ratio)

        self.frameleft_width = int(self.window_width * float(self.config_ini.get(
            self.config_section_name, 
            'ratio_between_width_of_frameleft_to_window_on_partsview')))
        self.frameleft_height = int(self.window_height)

        self.frameradio_width = int(self.frameleft_width)
        self.framesearch_width = int(self.frameleft_width)
        self.searchbutton_width = 4 #文字数指定
        self.framelistview_width = int(self.frameleft_width)

        self.frametopright_width = int(self.window_width - self.frameleft_width)
        self.frametopright_height = int(self.window_height * float(self.config_ini.get(
            self.config_section_name, 
            'ratio_between_height_of_frametopright_to_window_on_partsview')))

        self.framebottomright_width = int(self.frametopright_width)
        self.framebottomright_height = int(self.window_height - self.frametopright_height)

        self.canvas_width = int(self.frametopright_width)
        self.canvas_height = int(self.frametopright_height)

    def set_window_geometry(self):
        self.geometry(
            str(self.window_width) + 'x' + 
            str(self.window_height) + '+' + 
            str(int(self.screen_width/2-self.window_width/2 * 0.95)) + '+' + 
            str(int(self.screen_height/2-self.window_height/2 * 0.95)))

    def set_config(self):
        self.config_ini = configparser.ConfigParser()
        self.config_ini.read(self.config_path)

    def set_files(self):
        self.fig_file_name = 'parts.png'

    def set_events_forwin(self):
        self.listview.bind('<<TreeviewSelect>>', self.update_fig)
        self.partscanvas.tag_bind('img', '<ButtonPress-1>', self.image_pressed)
        self.partscanvas.tag_bind('img', '<B1-Motion>', self.image_dragged)
        self.partscanvas.bind('<Double-Button-1>', self.copy_parts)
        self.partscanvas.bind('<Enter>', self.add_label_oncanvas)
        self.partscanvas.bind('<Leave>', self.delete_label_oncanvas)
        self.entry_keyword.bind('<Key-Return>', self.serach_parts)

    def set_events_formac(self):
        self.listview.bind('<<TreeviewSelect>>', self.update_fig)
        self.partscanvas.tag_bind('img', '<ButtonPress-1>', self.image_pressed)
        self.partscanvas.tag_bind('img', '<B1-Motion>', self.image_dragged)
        self.partscanvas.bind('<Double-Button-1>', self.copy_parts)
        self.partscanvas.bind('<Enter>', self.add_label_oncanvas)
        self.partscanvas.bind('<Leave>', self.delete_label_oncanvas)
        self.entry_keyword.bind('<Key-Return>', self.serach_parts)

    def set_events(self):
        if self.os_name == 'Windows':self.set_events_forwin()
        if self.os_name == 'Mac':self.set_events_formac()

    def set_graph(self):
        self.graph = Digraph(format='png')
        self.graph.attr('graph', dpi='72')
        self.graph.attr(
            'node',
            shape=self.mainwindow.config_ini.get(self.mainwindow.config_section_name, 'node_shape'))
        self.graph.attr(
            'edge', 
            dir=self.mainwindow.config_ini.get(self.mainwindow.config_section_name, 'edge_direction'),
            arrowtail=self.mainwindow.config_ini.get(self.mainwindow.config_section_name, 'arrowtail'),
            arrowhead=self.mainwindow.config_ini.get(self.mainwindow.config_section_name, 'arrowhead'))

    def set_mainwindow(self, mainwindow):
        self.mainwindow = mainwindow

    def share_values_from_mainwindow(self):
        self.fig_dir = self.mainwindow.fig_dir
        self.capec_dir = self.mainwindow.capec_dir
        self.output_dir = self.mainwindow.output_dir
        self.config_path = self.mainwindow.config_path
        self.fontname_pattern = self.mainwindow.fontname_pattern
        self.fontcolor_pattern = self.mainwindow.fontcolor_pattern
        self.style_pattern = self.mainwindow.style_pattern
        self.fillcolor_pattern = self.mainwindow.fillcolor_pattern
        self.penwidth_pattern = self.mainwindow.penwidth_pattern

        self.fontname_free = self.mainwindow.fontname_free
        self.fontcolor_free = self.mainwindow.fontcolor_free
        self.style_free = self.mainwindow.style_free
        self.fillcolor_free = self.mainwindow.fillcolor_free
        self.penwidth_free = self.mainwindow.penwidth_free

        self.os_name = self.mainwindow.os_name
        self.config_section_name = self.mainwindow.config_section_name
        self.screen_height = self.mainwindow.screen_height
        self.screen_width = self.mainwindow.screen_width
        self.mainwindow_height = self.mainwindow.window_height
        self.mainwindow_width = self.mainwindow.window_width

    def pack_widgets(self):
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y)
        self.frame_radio.pack(side=tk.TOP, fill=tk.X)
        self.frame_search.pack(side=tk.TOP, fill=tk.X)
        self.frame_listview.pack(side=tk.TOP, fill=tk.BOTH)
        self.frame_toprigth.pack(side=tk.TOP, fill=tk.X)
        self.frame_bottomright.pack(side=tk.TOP, fill=tk.X)
        self.radio_reuse.pack(side=tk.LEFT, anchor=tk.W)
        self.radio_capec.pack(side=tk.LEFT, anchor=tk.W)
        self.button_serach.pack(side=tk.RIGHT, anchor=tk.W)
        self.entry_keyword.pack(side=tk.RIGHT, anchor=tk.W, fill=tk.BOTH, expand=True)
        self.listview_xbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.listview_ybar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listview.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.partscanvas.pack(fill=tk.BOTH)
        self.reuse_conditions.pack(side=tk.TOP, fill=tk.X)

    def update_fig(self, event=None):
        selected_iid = self.listview.focus()
        ancestor_iid = self.get_ancestor(selected_iid)
        parts_tuple = self.get_parts(ancestor_iid)
        condition_iid_list = self.get_conditions(ancestor_iid)
        rawcondition_iid_list = self.get_rawconditions(ancestor_iid)
        parts_parent_iid = self.get_parts_parent(ancestor_iid)

        self.graph.clear()
        self.set_graph()
        self.add_subtree_tograph(parts_tuple, parts_parent_iid)

        #pngファイル出力
        fig_body = Path(self.fig_file_name).stem

        try:
            self.graph.render(os.path.join(self.fig_dir, fig_body))
        except Exception as e:
            messagebox.askokcancel('Exception', e)

        self.img_x = self.partscanvas.winfo_width()/2
        self.img_y = self.partscanvas.winfo_height()/2

        #pngファイル読み込み
        fig_path = os.path.join(self.fig_dir, self.fig_file_name)
        self.partsimage_raw = Image.open(fig_path)
        self.partsimage_tk = ImageTk.PhotoImage(self.partsimage_raw)
        self.partscanvas.create_image(
            self.img_x, 
            self.img_y, 
            image=self.partsimage_tk, 
            anchor=tk.CENTER, 
            tags='img')

        #テキストボックスを編集可能にする
        self.reuse_conditions.configure(state='normal')
        self.reuse_conditions.delete(0.,tk.END)

        if len(condition_iid_list) == 0:
            self.add_conditions('適用（再利用）条件はありません．\n')
        else:
            self.add_conditions('適用（再利用）条件\n')

            for i, condition_iid in enumerate(condition_iid_list):
                condition = self.listview.item(condition_iid, 'text')
                self.add_conditions('  '+str(i+1) + '. ' + condition + '\n')

        if len(rawcondition_iid_list) != 0:
            self.add_conditions('\nPrerequisites(英語)\n')

            for i, rawcondition_iid in enumerate(rawcondition_iid_list):
                rawcondition = self.listview.item(rawcondition_iid, 'text')
                self.add_conditions('  '+str(i+1) + '. ' + rawcondition + '\n')

        #テキストボックスを編集不可にする
        self.reuse_conditions.configure(state='disabled')
