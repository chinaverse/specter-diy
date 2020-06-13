import lvgl as lv
from .common import *
from .decorators import *
from .components import MnemonicTable, HintKeyboard
import rng
import asyncio

class Screen(lv.obj):
    def __init__(self):
        super().__init__()
        self.waiting = True
        self._value = None

    def release(self):
        self.waiting = False

    def get_value(self):
        """
        Redefine this function to get value entered by the user
        """
        return self._value

    def set_value(self, value):
        self._value = value
        self.release()

    async def result(self):
        self.waiting = True
        while self.waiting:
            await asyncio.sleep_ms(1)
        return self.get_value()

class PinScreen(Screen):
    def __init__(self, title="Enter your PIN code", note=None, get_word=None):
        super().__init__()
        self.title = add_label(title, scr=self, y=PADDING, style="title")
        if note is not None:
            lbl = add_label(note, scr=self, style="hint")
            lbl.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 180)
        self.get_word = get_word
        if get_word is not None:
            self.words = add_label(get_word(b""), scr=self)
            self.words.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 210)
        btnm = lv.btnm(self)
        # shuffle numbers to make sure 
        # no constant fingerprints left on screen
        buttons = ["%d" % i for i in range(0,10)]
        btnmap = []
        for j in range(3):
            for i in range(3):
                v = rng.get_random_bytes(1)[0] % len(buttons)
                btnmap.append(buttons.pop(v))
            btnmap.append("\n")
        btnmap = btnmap+[lv.SYMBOL.CLOSE, buttons.pop(), lv.SYMBOL.OK, ""]
        btnm.set_map(btnmap)
        btnm.set_width(HOR_RES)
        btnm.set_height(HOR_RES)
        btnm.align(self, lv.ALIGN.IN_BOTTOM_MID, 0, 0)
        # remove feedback on press to avoid sidechannels
        btnm.set_style(lv.btnm.STYLE.BTN_PR,btnm.get_style(lv.btnm.STYLE.BTN_REL))

        self.pin = lv.ta(self)
        self.pin.set_text("")
        self.pin.set_pwd_mode(True)
        style = lv.style_t()
        lv.style_copy(style, styles["theme"].style.ta.oneline)
        style.text.font = lv.font_roboto_28
        style.text.color = lv.color_hex(0xffffff)
        style.text.letter_space = 15
        self.pin.set_style(lv.label.STYLE.MAIN, style)
        self.pin.set_width(HOR_RES-2*PADDING)
        self.pin.set_x(PADDING)
        self.pin.set_y(PADDING+50)
        self.pin.set_cursor_type(lv.CURSOR.HIDDEN)
        self.pin.set_one_line(True)
        self.pin.set_text_align(lv.label.ALIGN.CENTER)
        self.pin.set_pwd_show_time(0)
        self.pin.align(btnm, lv.ALIGN.OUT_TOP_MID, 0, -150)

        btnm.set_event_cb(self.cb);

    def reset(self):
        self.pin.set_text("")
        if self.get_word is not None:
            self.words.set_text(self.get_word(b""))

    @feed_rng
    def cb(self, obj, event):
        if event == lv.EVENT.RELEASED:
            c = obj.get_active_btn_text()
            if c is None:
                return
            if c == lv.SYMBOL.CLOSE:
                self.reset()
            elif c == lv.SYMBOL.OK:
                self.release()
            else:
                self.pin.add_text(c)
                # add new anti-phishing word
                if self.get_word is not None:
                    cur_words = self.words.get_text()
                    cur_words += " "+self.get_word(self.pin.get_text())
                    self.words.set_text(cur_words)


    def get_value(self):
        return self.pin.get_text()

class MenuScreen(Screen):
    def __init__(self, buttons=[], 
                 title="What do you want to do?", note=None,
                 y0=100, last=None
                 ):
        super().__init__()
        y = y0
        self.title = add_label(title, style="title", scr=self)
        if note is not None:
            self.note = add_label(note, style="hint", scr=self)
            self.note.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 5)
            y += self.note.get_height()
        for value, text in buttons:
            if text is not None:
                if value is not None:
                    add_button(text, 
                        on_release(
                            cb_with_args(self.set_value, value)
                        ), y=y, scr=self)
                    y+=85
                else:
                    add_label(text.upper(), y=y+10, style="hint", scr=self)
                    y+=50
            else:
                y+=40
        if last is not None:
            self.add_back_button(*last)

    def add_back_button(self, value, text=None):
        if text is None:
            text = lv.SYMBOL.LEFT+" Back"
        add_button(text, 
                on_release(
                        cb_with_args(self.set_value, value)
                ), scr=self)


class Alert(Screen):
    def __init__(self, title, message, button_text=(lv.SYMBOL.LEFT+" Back")):
        super().__init__()
        self.title = add_label(title, scr=self, style="title")
        self.page = lv.page(self)
        self.page.set_size(480, 600)
        self.message = add_label(message, scr=self.page)
        self.page.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)

        self.close_button = add_button(scr=self, 
                                callback=on_release(self.release))

        self.close_label = lv.label(self.close_button)
        self.close_label.set_text(button_text)

class Prompt(Screen):
    def __init__(self, title="Are you sure?", message="Make a choice"):
        super().__init__()
        self.title = add_label(title, scr=self, style="title")
        self.page = lv.page(self)
        self.page.set_size(480, 600)
        self.message = add_label(message, scr=self.page)
        self.page.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)

        (self.cancel_button, 
         self.confirm_button) = add_button_pair(
                    "Cancel", on_release(cb_with_args(self.set_value,False)), 
                    "Confirm", on_release(cb_with_args(self.set_value,True)), 
                    scr=self)

class QRAlert(Alert):
    def __init__(self,
                 title="QR Alert!", 
                 message="Something happened", 
                 qr_message=None,
                 qr_width=None,
                 button_text="Close"):
        if qr_message is None:
            qr_message = message
        super().__init__(title, message, button_text)
        self.qr = add_qrcode(qr_message, scr=self, width=qr_width)
        self.qr.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 50)
        self.message.align(self.qr, lv.ALIGN.OUT_BOTTOM_MID, 0, 50)

class MnemonicScreen(Screen):
    def __init__(self, title="Your recovery phrase", note=None, mnemonic=""):
        super().__init__()
        self.title = add_label(title, scr=self, style="title")
        if note is not None:
            lbl = add_label(note, scr=self, style="hint")
            lbl.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 5)
        self.table = MnemonicTable(self)
        self.table.set_mnemonic(mnemonic)
        self.table.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 30)

        self.close_button = add_button(scr=self, 
                                callback=on_release(self.release))

        self.close_label = lv.label(self.close_button)
        self.close_label.set_text("OK")

class NewMnemonicScreen(MnemonicScreen):
    def __init__(self, generator, title="Your recovery phrase:", 
            note="Write it down and never show to anybody"):
        mnemonic = generator(12)
        super().__init__(title, note, mnemonic)
        self.table.align(self.title, lv.ALIGN.OUT_BOTTOM_MID, 0, 50)

        self.close_label.set_text(lv.SYMBOL.LEFT+" Back")
        self.next_button = add_button(scr=self, 
                                callback=on_release(self.confirm))

        self.next_label = lv.label(self.next_button)
        self.next_label.set_text("Next "+lv.SYMBOL.RIGHT)
        align_button_pair(self.close_button, self.next_button)

        lbl = lv.label(self)
        lbl.set_text("Use 24 words")
        lbl.align(self.table, lv.ALIGN.OUT_BOTTOM_MID, 0, 60)
        lbl.set_x(120)

        self.switch = lv.sw(self)
        self.switch.off(lv.ANIM.OFF)
        self.switch.align(lbl, lv.ALIGN.OUT_RIGHT_MID, 20, 0)

        def cb():
            wordcount = 24 if self.switch.get_state() else 12
            self.table.set_mnemonic(generator(wordcount))

        self.switch.set_event_cb(on_release(cb))


    def confirm(self):
        self.set_value(self.table.get_mnemonic())

class RecoverMnemonicScreen(MnemonicScreen):
    def __init__(self, checker=None, lookup=None, 
                 title="Enter your recovery phrase"):
        super().__init__(title)
        self.checker = checker
        self.lookup = lookup

        self.close_button.del_async()
        self.close_button = None
        self.kb = HintKeyboard(self)
        self.kb.set_map([
            "Q","W","E","R","T","Y","U","I","O","P","\n",
            "A","S","D","F","G","H","J","K","L","\n",
            "Z","X","C","V","B","N","M",lv.SYMBOL.LEFT,"\n",
            lv.SYMBOL.LEFT+" Back","Next word",lv.SYMBOL.OK+" Done",""
        ])

        if lookup is not None:
            # Next word button inactive
            self.kb.set_btn_ctrl(28, lv.btnm.CTRL.INACTIVE)
        if checker is not None:
            # Done inactive
            self.kb.set_btn_ctrl(29, lv.btnm.CTRL.INACTIVE)
        self.kb.set_width(HOR_RES)
        self.kb.set_height(VER_RES//3)
        self.kb.align(self, lv.ALIGN.IN_BOTTOM_MID, 0, 0)
        self.kb.set_event_cb(self.callback)

    def callback(self, obj, event):
        if event != lv.EVENT.RELEASED:
            return
        c = obj.get_active_btn_text()
        if c is None:
            return
        num = obj.get_active_btn()
        # if inactive button is clicked - return
        if obj.get_btn_ctrl(num,lv.btnm.CTRL.INACTIVE):
            return
        if c == lv.SYMBOL.LEFT+" Back":
            self.set_value(None)
        elif c == lv.SYMBOL.LEFT:
            self.table.del_char()
        elif c == "Next word":
            word = self.table.get_last_word()
            if self.lookup is not None and len(word)>=2:
                candidates = self.lookup(word)
                if len(candidates) == 1:
                    self.table.autocomplete_word(candidates[0])
        elif c == lv.SYMBOL.OK+" Done":
            pass
        else:
            self.table.add_char(c.lower())

        mnemonic = self.table.get_mnemonic()
        if self.lookup is not None:
            self.kb.set_btn_ctrl(28, lv.btnm.CTRL.INACTIVE)
            word = self.table.get_last_word()
            candidates = self.lookup(word)
            if len(candidates) == 1 or word in candidates:
                self.kb.clear_btn_ctrl(28, lv.btnm.CTRL.INACTIVE)
                if len(candidates) == 1:
                    mnemonic = " ".join(self.table.words[:-1])
                    mnemonic += " "+candidates[0]
        mnemonic = mnemonic.strip()
        if self.checker is not None and mnemonic is not None:
            if self.checker(mnemonic):
                self.kb.clear_btn_ctrl(29, lv.btnm.CTRL.INACTIVE)
            else:
                self.kb.set_btn_ctrl(29, lv.btnm.CTRL.INACTIVE)
        # if user was able to click this button then mnemonic is correct
        if c == lv.SYMBOL.OK+" Done":
            self.set_value(mnemonic)
