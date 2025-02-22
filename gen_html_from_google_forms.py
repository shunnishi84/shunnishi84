import sys
import re
import os
import platform
import math
import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import base64
import configparser
import japanize_matplotlib

from io import BytesIO

NOT_OTHERS = ['所属部署', '勤続年数']
CSS_FILE = './static/style.css'
try:
    with open(CSS_FILE, 'r') as f:
        plain_css = f.read()
except FileNotFoundError:
    print('style.css not found.')
    sys.exit(1)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)

CSS = f"""
<style>
{plain_css}
</style>
"""


def get_graph_font():
    """OSに応じたグラフの日本語フォントを返す。"""
    FONTS = './static/fonts.ini'
    config = configparser.ConfigParser()
    config.read(FONTS)
    os_name = platform.system()

    config_dict  = {section: dict(config.items(section)) for section in config.sections()}

    return config_dict[os_name]['font']


def plot_to_base64(labels, sizes):
    """グラフを描画してbase64エンコードされたimgタグを返す。"""
    plt.figure(figsize=(6, 6))
    japanize_matplotlib.japanize()
    plt.pie(sizes, autopct='%1.1f%%', shadow=True, startangle=90)
    plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), labels=labels)
    png_image = BytesIO()
    plt.savefig(png_image, format='png', bbox_inches='tight', dpi=100)
    plt.clf()
    plt.close()
    encoded = base64.b64encode(png_image.getvalue()).decode('utf-8')

    return f'<img src="data:image/png;base64,{encoded}">'


def convert_from_answer_to_dict(fname):
    """回答をdictに変換する。"""
    df = pd.read_excel(fname)
    ans = {col: df[col].value_counts().to_dict() for col in df.columns}
    for q, ans_dict in ans.items():
        tmp = {}
        for a in ans_dict:
            line = str(a).split(", ")
            if len(line) == 1:
                continue
            for v in line:
                tmp[v] = tmp.get(v, 0) + 1
            ans[q] = tmp
    return ans


def get_percentage(cnt, nums):
    """回答率を計算する。"""
    return f'{math.floor((cnt / sum(nums)) * 10000) / 100}%'


def format_text(intext):
    """フリーアンサーをフォーマットする。"""
    response = ""
    for a in intext.split(" ・"):
        a = re.sub(r'^・', '', a)
        a = re.sub(r'\- ', '<br>', re.sub(r'^\-', '', a))
        a = re.sub(r'## ', '<li>', a)
        a = re.sub(r'\<li\>\<li\>', '', a)
        if a:
            response += f'<li>{a}</li>\n'
    return response


def print_html(data):
    """回答のdictをHTML化して出力する。"""
    html_base = f"""
<!DOCTYPE html>
<HTML><HEAD>{CSS}</HEAD><BODY>"""
    print(html_base)
    q_cnt = 1

    for q, ans in data.items():
        if q == 'タイムスタンプ':
            continue
        only_free_answer = (max(ans.values()) == 1)
        other_ans = []
        plot_ans = {}
        title = f'<h2>Q{q_cnt}. {q}</h2>'
        table_header = "<table><thead><tr><th>回答</th>\
                        <th>回答数</th><th>回答割合</th></tr></thead>"
        tables = ""

        if not only_free_answer:
            for a, cnt in ans.items():
                if cnt > 1 or q in NOT_OTHERS:
                    plot_ans[a] = cnt
                    tables += f'<tr><td>{a}</td><td class=count>{cnt}</td>\
                    <td class=count>{get_percentage(cnt, ans.values())}\
                    </td></tr>\n'
                else:
                    other_ans.append(a)
                    plot_ans['その他'] = plot_ans.get('その他', 0) + 1

            print(title)
            print(plot_to_base64(plot_ans.keys(), plot_ans.values()))
            print(table_header + tables + "</table>")

            if other_ans:
                print("<h3>その他には以下のような回答が寄せられています</h3>")
                for a in other_ans:
                    print(format_text(a))
        else:
            print(title)
            for key in ans.keys():
                print(format_text(key))

        q_cnt += 1
    print("</BODY></HTML>")


def main():
    if len(sys.argv) != 2:
        print("Usage: python gen_html_from_google_forms.py <filename>")
        sys.exit(1)

    fname = sys.argv[1]
    if not os.path.exists(fname):
        print(f'{fname} not found.')
        sys.exit(1)

    mpl.rcParams['font.family'] = get_graph_font()
    data = convert_from_answer_to_dict(fname)
    print_html(data)


if __name__ == '__main__':
    main()
