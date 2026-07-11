(function () {
    'use strict';

    const exact = new Map(Object.entries({
        'Library': '游戏库', 'Requests': '请求', 'Request': '请求', 'Content': '内容',
        'Downloads': '下载', 'Upload': '上传', 'Cheats': '金手指', 'Manage': '管理', 'Backups': '备份',
        'Save Data Backups': '存档备份', 'Admin': '管理', 'Users': '用户',
        'Activity': '活动记录', 'Settings': '设置', 'Login': '登录', 'Logout': '退出登录',
        'Username': '用户名', 'Password': '密码', 'Remember me': '记住我', 'User': '用户',
        'Search': '搜索', 'Filter': '筛选', 'Clear': '清除', 'Reset': '重置',
        'Save': '保存', 'Cancel': '取消', 'Close': '关闭', 'Delete': '删除',
        'Remove': '移除', 'Add': '添加', 'Edit': '编辑', 'Refresh': '刷新',
        'Retry': '重试', 'Start': '开始', 'Stop': '停止', 'Run': '运行',
        'Enabled': '已启用', 'Disabled': '已禁用', 'Status': '状态', 'Actions': '操作',
        'Name': '名称', 'Type': '类型', 'Version': '版本', 'Size': '大小',
        'Path': '路径', 'File': '文件', 'Files': '文件', 'Title': '标题',
        'Title ID': 'Title ID', 'App ID': 'App ID', 'Created': '创建时间',
        'Updated': '更新时间', 'Progress': '进度', 'Error': '错误', 'Success': '成功',
        'Warning': '警告', 'Details': '详情', 'Download': '下载', 'Install': '安装',
        'Queued': '已排队', 'Downloading': '下载中', 'Completed': '已完成',
        'Failed': '失败', 'Running': '运行中', 'Ready': '就绪', 'Stuck': '待处理',
        'Public shop': '公开商店', 'Fast transfer mode': '高速传输模式',
        'Access And Delivery': '访问与传输', 'Login Protection': '登录保护',
        'Keys And Branding': '密钥与品牌', 'Message of the day:': '每日消息：',
        'Save shop settings': '保存商店设置', 'Metadata locale': '元数据区域与语言',
        'Title Identification': '游戏识别', 'Add library path': '添加游戏库路径',
        'Upload keys': '上传密钥', 'Public Key:': '公钥：', 'Show': '显示', 'Copy': '复制',
        'Library: Ready': '游戏库：就绪', 'Library: Scanning': '游戏库：扫描中',
        'Library: Rebuilding': '游戏库：重建中', 'Library: Updating TitleDB': '游戏库：更新 TitleDB',
        'Library size: ...': '游戏库大小：…', 'No results found.': '未找到结果。',
        'No data available.': '暂无数据。', 'Loading...': '加载中…', 'Uploading...': '上传中…',
        'Select all': '全选', 'Deselect all': '取消全选', 'Previous': '上一页', 'Next': '下一页',
        'Game': '游戏', 'Games': '游戏', 'Base': '本体', 'Update': '更新', 'Updates': '更新',
        'DLC': 'DLC', 'Region': '区域', 'Language': '语言', 'Description': '简介',
        'Organize library': '整理游戏库', 'Delete duplicates': '删除重复文件',
        'Delete older updates': '删除旧更新', 'Dry run': '仅预览', 'Scan library': '扫描游戏库',
        'Maintenance': '维护', 'Library organization': '游戏库整理', 'Library scan': '游戏库扫描',
        'Task output': '任务输出', 'Recent jobs': '最近任务', 'Diagnostics': '诊断信息',
        'Converter ready': '转换器就绪', 'Verbose': '详细输出', 'No jobs yet.': '暂无任务。',
        'Expand': '展开', 'Collapse': '收起', 'Loading diagnostics...': '正在加载诊断信息…',
        'Library maintenance actions and converter jobs.': '游戏库维护操作和格式转换任务。',
        'Organize and clean up your libraries.': '整理并清理游戏库。',
        'Rename and organize identified content into structured folders.': '将已识别内容重命名并整理到结构化目录。',
        'Scan configured libraries for new files.': '扫描已配置的游戏库以查找新文件。',
        'Keep the latest owned update per title and remove older update files.': '每款游戏保留最新更新，并移除旧更新文件。',
        'Drag & drop files here': '将文件拖放到这里', 'or click to browse': '或点击选择文件',
        'Choose where to place your uploaded files.': '选择上传文件要保存到的游戏库。',
        'Allowed: NSP, NSZ, XCI, XCZ. Large uploads may take a while.': '支持 NSP、NSZ、XCI、XCZ，大文件上传需要一些时间。',
        'Select at least one file.': '请至少选择一个文件。', 'Clear list': '清空列表',
        'Profile': '个人资料', 'Email': '邮箱', 'Role': '角色', 'Administrator': '管理员',
        'Create user': '创建用户', 'Invite user': '邀请用户', 'Pending': '等待中'
    }));

    const patterns = [
        [/^Library size:\s*/i, '游戏库大小：'],
        [/^Uploaded (\d+) files?\.?(?: Skipped (\d+)\.)?$/i, (_, a, b) => `已上传 ${a} 个文件${b ? `，跳过 ${b} 个` : ''}。`],
        [/^Conversion:\s*(.*)$/i, (_, value) => `转换：${value}`],
        [/^Conversion running$/i, '转换正在运行'],
        [/^Page (\d+) of (\d+)$/i, (_, a, b) => `第 ${a} 页，共 ${b} 页`],
        [/^(\d+) files?$/i, (_, n) => `${n} 个文件`],
        [/^No (.*) configured\.?$/i, (_, value) => `尚未配置${value}。`]
    ];

    function translate(value) {
        const source = String(value || '');
        const trimmed = source.trim();
        if (!trimmed) return source;
        if (exact.has(trimmed)) return source.replace(trimmed, exact.get(trimmed));
        for (const [regex, replacement] of patterns) {
            if (regex.test(trimmed)) {
                regex.lastIndex = 0;
                const output = typeof replacement === 'function' ? trimmed.replace(regex, replacement) : trimmed.replace(regex, replacement);
                return source.replace(trimmed, output);
            }
        }
        return source;
    }

    function translateElement(root) {
        if (!root || root.nodeType !== Node.ELEMENT_NODE) return;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                const parent = node.parentElement;
                if (!parent || ['SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA'].includes(parent.tagName)) return NodeFilter.FILTER_REJECT;
                return /[A-Za-z]/.test(node.nodeValue || '') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
            }
        });
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(node => {
            const translated = translate(node.nodeValue);
            if (translated !== node.nodeValue) node.nodeValue = translated;
        });

        root.querySelectorAll('input[placeholder], textarea[placeholder], [title], [aria-label]').forEach(el => {
            ['placeholder', 'title', 'aria-label'].forEach(attr => {
                if (el.hasAttribute(attr)) {
                    const current = el.getAttribute(attr);
                    const translated = translate(current);
                    if (translated !== current) el.setAttribute(attr, translated);
                }
            });
        });
    }

    function boot() {
        document.title = document.title.replace(/\bLibrary\b/g, '游戏库').replace(/\bSettings\b/g, '设置')
            .replace(/\bDownloads\b/g, '下载').replace(/\bUpload\b/g, '上传').replace(/\bManage\b/g, '管理')
            .replace(/\bLogin\b/g, '登录').replace(/\bUsers\b/g, '用户').replace(/\bActivity\b/g, '活动记录');
        translateElement(document.body);
        let scheduled = false;
        const observer = new MutationObserver(() => {
            if (scheduled) return;
            scheduled = true;
            requestAnimationFrame(() => { scheduled = false; translateElement(document.body); });
        });
        observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
})();
