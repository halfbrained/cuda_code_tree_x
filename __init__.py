import os
from contextlib import contextmanager

from cudatext import *


fn_config = os.path.join(app_path(APP_DIR_SETTINGS), 'plugins.ini')

CFG_SECTION = 'code_tree_x'

opt_fn_icon   = os.path.join(os.path.dirname(__file__), 'icon.png')


@contextmanager
def lock_tree(h_tree):
    from time import time as t
    _t0 = t()

    tree_proc(h_tree, TREE_LOCK)
    try:
        yield
    finally:
        tree_proc(h_tree, TREE_UNLOCK)
    _t1 = t()
    print(f'NOTE: updated tree in : {_t1-_t0:.3f}')

class Command:

    def __init__(self):
        global opt_fn_icon

        opt_fn_icon = ini_read(fn_config, CFG_SECTION, 'icon', opt_fn_icon)

        self.h_tree = app_proc(PROC_GET_CODETREE, '')
        self._bm_im_ind = None

    def _init(self):
        h_im = tree_proc(self.h_tree, TREE_GET_IMAGELIST)
        self._bm_im_ind = imagelist_proc(h_im, IMAGELIST_ADD, opt_fn_icon)

    def config(self):
        ini_write(fn_config, CFG_SECTION, 'icon', opt_fn_icon)
        file_open(fn_config)

    def on_state(self, ed_self, state):
        if state == APPSTATE_CODETREE_AFTER_FILL:
            with lock_tree(self.h_tree):
                self._fill_tree()

    def on_state_ed(self, ed_self, state):
        if state == EDSTATE_BOOKMARK:
            with lock_tree(self.h_tree):
                self._clear_my_tree_stuff()
                self._fill_tree()

    def _fill_tree(self):
        bookmarks = ed.bookmark(BOOKMARK_GET_ALL, 0)
        if not bookmarks:
            return
        if self._bm_im_ind is None:
            self._init()

        # gather tree-placement for each bookmark
        tree_adds = []
        prev_level = 0
        for (id_parent, range_, ind, level) in self._get_tree_items():
            #print(f' tree item: {id_parent, ind, range_, },lvl:{prev_level}>{level}')
            while bookmarks:
                if range_[1] >= bookmarks[0]['line']:
                    bmdict = bookmarks.pop(0)
                    if bmdict['kind'] > 8:
                        continue

                    nline = bmdict['line']
                    line_txt = ed.get_text_substr(0,nline, 128,nline).strip()

                    if prev_level == level:     # same level
                        i_id_parent = id_parent
                        i_ind = ind
                    elif prev_level < level:    # gone deeper
                        i_id_parent = id_parent
                        i_ind = 0
                    else:                       # gone up a lavel
                        i_id_parent = id_parent
                        i_ind = ind

                    #print(f'    + adding: {i_ind, i_id_parent} :: {line_txt}')
                    _vargs = {'id_item':i_id_parent,  'text':line_txt,  'index':i_ind}
                    tree_adds.append((nline, _vargs))
                else:
                    break

            if not bookmarks:   break

            prev_level = level
        #end for

        # add gathered bookmarks to code-tree
        for nline,tree_vargs in reversed(tree_adds):
            id_item = tree_proc(self.h_tree, TREE_ITEM_ADD, image_index=self._bm_im_ind,  **tree_vargs)
            tree_proc(self.h_tree, TREE_ITEM_SET_RANGE,  id_item=id_item,  text=(0,nline, 1,nline))


    def _clear_my_tree_stuff(self, id_parent=0):
        """ remove all code-tree items with image=`_bm_im_ind`
        """
        items = tree_proc(self.h_tree, TREE_ITEM_ENUM_EX, id_item=id_parent) # [(id_item, name), ...]
        if not items:   return

        for item in items:
            if item['img'] == self._bm_im_ind:
                tree_proc(self.h_tree, TREE_ITEM_DELETE,  id_item=item['id'])
            elif item['sub_items']:
                self._clear_my_tree_stuff(item['id'])


    def _get_tree_items(self, id_parent=0, level=0):
        """ for every tree item yields a tuple:
                (item id,  item range,  index in parent,  level in tree:0)
        """
        items = tree_proc(self.h_tree, TREE_ITEM_ENUM, id_item=id_parent) # [(id_item, name), ...]
        if not items:   return

        for i,item in enumerate(items):
            id_item = item[0]
            range_ = tree_proc(self.h_tree, TREE_ITEM_GET_RANGE, id_item=id_item)
            if range_[0] != -1:
                yield (id_parent, range_, i, level)

            yield from self._get_tree_items(id_item, level+1)

        if id_parent == 0:  # last - fake item - to place bookmarks beyond real last item
            yield (0, (0,2**30, 0,2**30), len(items), 0)
