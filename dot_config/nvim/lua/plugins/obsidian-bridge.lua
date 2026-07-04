require("obsidian-bridge").setup({
    obsidian_server_address = "https://127.0.0.1:27124",
    scroll_sync = true,
    cert_path = '~/.ssl/obsidian.crt',
    warnings = true,
    picker = 'telescope'
})
