import requests
import api.wbi as wbi
import pandas as pd
from const_data import headers
import json
import gradio as gr
import time
import os

def get_videos_info(mid, pn=1, custom_cookies=None):
    """ 
    获取视频信息
    mid: 用户id
    pn: 页码
    custom_cookies: 用户的cookie
    """
    if not custom_cookies:
        raise Exception("请提供Cookie以继续爬取")
        
    params = {
        "mid": mid,
        "pn": pn,
        "dm_img_list": "[]",
        "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
        "dm_cover_img_str": "QU5HTEUgKEludGVsLCBJbnRlbChSKSBVSEQgR3JhcGhpY3MgKDB4MDAwMDlCQzQpIERpcmVjdDNEMTEgdnNfNV8wIHBzXzVfMCwgRDNEMTEpR29vZ2xlIEluYy4gKEludGVsKQ",
    }
    params = wbi.sign(params)
    
    response = requests.get(
        'https://api.bilibili.com/x/space/wbi/arc/search',
        params=params, 
        cookies=custom_cookies, 
        headers=headers
    )
    if response.json()['code'] == 0:
        return response.json()['data']
    else:
        raise Exception("爬取视频信息失败，请检查Cookie是否有效")

def get_vlist_info(vlist):
    """ ::
    获取视频信息:
    vlist: 视频列表
    """
    list = []
    for v in vlist:
        title = v['title']
        play = v['play']
        length = v['length']
        list.append([title, play, length])
    return list

def crawl_up_videos(mid, progress=gr.Progress(), custom_cookies=None):
    """
    爬取UP主视频信息的主函数
    mid: UP主ID
    progress: gradio进度条对象
    custom_cookies: 自定义cookie
    """
    try:
        # 1.获取第一页视频信息,.
        pre_data = get_videos_info(mid, custom_cookies=custom_cookies)
        
        # 2.获取视频信息[page,list],
        page = pre_data['page']
        video_list = pre_data['list']

        # 3.获取视频总页数
        count, ps = page['count'], page['ps']
        page_size = count // ps + (1 if count % ps else 0)
        
        # 4.获取全部视频
        data_list = []
        data_list.extend(video_list['vlist'])
        
        # 使用progress.tqdm包装循环以显示进度
        for i in progress.tqdm(range(2, page_size + 1), desc="正在爬取视频信息"):
            data = get_videos_info(mid, i, custom_cookies=custom_cookies)
            data_list.extend(data['list']['vlist'])
            time.sleep(0.5)  # 添加延迟避免请求过快
        # 5.获取视频信息:
        info_list = get_vlist_info(data_list)
        
        # 6.转换为DataFrame
        df = pd.DataFrame(info_list, columns=['标题', '播放量', '时长'])
        
        # 7.保存数据:/
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_path = f'data/up_{mid}_{timestamp}.csv'
        json_path = f'data/up_{mid}_{timestamp}.json'
        raw_json_path = f'data/up_{mid}_{timestamp}_raw.json'
        
        # 确保data目录存在
        os.makedirs('data', exist_ok=True)
        
        # 保存CSV和处理后的JSON
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        df.to_json(json_path, force_ascii=False, orient='records', indent=2)
        
        # 保存原始数据
        with open(raw_json_path, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        
        return (
            df, 
            f"爬取完成！共获取 {len(info_list)} 个视频信息\n数据已保存至：\nCSV: {csv_path}\nJSON: {json_path}\n原始数据: {raw_json_path}",
            csv_path,
            json_path,
            raw_json_path
        )
        
    except Exception as e:
        return None, f"爬取失败：{str(e)}", None, None, None

def parse_cookie(cookie_str):
    """解析Cookie字符串为字典"""
    if not cookie_str:
        raise Exception("请提供Cookie")
    
    cookie_dict = {}
    try:
        # 处理多行cookie字符串
        cookie_str = cookie_str.replace('\n', ';')
        for item in cookie_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookie_dict[key.strip()] = value.strip()
        
        # 验证必要的cookie字段
        required_cookies = ['SESSDATA', 'bili_jct', 'buvid3']
        missing_cookies = [key for key in required_cookies if key not in cookie_dict]
        if missing_cookies:
            raise Exception(f"Cookie缺少必要字段: {', '.join(missing_cookies)}")
            
        return cookie_dict
    except Exception as e:
        raise Exception(f"Cookie解析失败: {str(e)}")

def create_ui():
    """
    创建Gradio界面
    """
    with gr.Blocks(title="B站UP主视频爬虫", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# B站UP主视频信息爬虫")
        gr.Markdown("输入UP主的ID(mid)和Cookie，获取其所有视频的信息。")
        
        with gr.Row():
            mid_input = gr.Textbox(label="UP主ID", placeholder="请输入UP主ID(mid)")
            cookie_input = gr.Textbox(
                label="Cookie(必填)", 
                placeholder="请输入自己的Cookie，从浏览器开发者工具中复制,格式：key1=value1; key2=value2; key3=value3",
                lines=3
            )
        
        with gr.Row():
            crawl_btn = gr.Button("开始爬取", variant="primary")
            
        with gr.Row():
            with gr.Column(scale=2):
                status_output = gr.Textbox(label="状态信息", interactive=False, lines=4)
                with gr.Row():
                    csv_download = gr.File(label="下载CSV", visible=False, interactive=True)
                    json_download = gr.File(label="下载JSON", visible=False, interactive=True)
                    raw_json_download = gr.File(label="下载原始数据", visible=False, interactive=True)
            
            with gr.Column(scale=1):
                gr.Markdown("""
                ### 说明
                - 数据将自动保存在 data 目录下
                - 文件名格式：up_[mid]_[时间戳].[格式]
                - 支持下载三种格式：
                  1. CSV：处理后的表格数据
                  2. JSON：处理后的结构化数据
                  3. 原始数据：包含完整的视频信息
                - CSV文件使用UTF-8编码，Excel打开请注意编码设置
                - Cookie说明：
                  - 必须提供自己的Cookie才能使用
                  - 从浏览器登录B站后，按F12打开开发者工具
                  - 在Network标签页中找到任意请求的Cookie
                  - Cookie中必须包含：SESSDATA、bili_jct、buvid3
                  - 格式：key1=value1; key2=value2; key3=value3
                  - Cookie仅在本地使用，不会上传或保存
                """)
            
        output_df = gr.DataFrame(label="视频信息")
        
        def show_downloads(mid, cookie_str):
            """处理爬虫结果并控制下载按钮的显示"""
            try:
                # 解析cookie
                custom_cookies = parse_cookie(cookie_str)
                
                # 调用爬虫函数获取结果，传入自定义cookie
                df, status, csv_path, json_path, raw_path = crawl_up_videos(
                    mid, 
                    progress=gr.Progress(),
                    custom_cookies=custom_cookies
                )
                
                # 检查文件是否存在
                files_exist = all(path is not None for path in [csv_path, json_path, raw_path])
                
                return [
                    df, 
                    status,
                    gr.update(value=csv_path, visible=files_exist),
                    gr.update(value=json_path, visible=files_exist),
                    gr.update(value=raw_path, visible=files_exist)
                ]
            except Exception as e:
                return [
                    None,
                    f"发生错误：{str(e)}",
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False)
                ]
        
        crawl_btn.click(
            fn=show_downloads,
            inputs=[mid_input, cookie_input],
            outputs=[
                output_df,
                status_output,
                csv_download,
                json_download,
                raw_json_download
            ]
        )
    
    return demo

if __name__ == '__main__':
    demo = create_ui()
    demo.launch(share=False, server_name="0.0.0.0")
