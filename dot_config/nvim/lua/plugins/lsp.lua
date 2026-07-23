local capabilities = require("blink.cmp").get_lsp_capabilities()

vim.lsp.config("clangd", {
  cmd = { "clangd" },
  filetypes = { "c", "cpp", "objc", "objcpp" },
  root_markers = { "compile_commands.json", ".clangd", ".git" },
  capabilities = capabilities,
})

vim.lsp.config("basedpyright", {
  cmd = { "basedpyright-langserver", "--stdio" },
  filetypes = { "python" },
  root_markers = { "pyproject.toml", "setup.py", ".git" },
  capabilities = capabilities,
})

vim.lsp.config("lua_ls", {
  cmd = { "lua-language-server" },
  filetypes = { "lua" },
  root_markers = { ".luarc.json", "stylua.toml", ".git" },
  capabilities = capabilities,
  settings = {
    Lua = {
      workspace = { checkThirdParty = false },
      telemetry = { enable = false },
    },
  },
})

vim.lsp.enable({ "clangd", "basedpyright", "lua_ls" })

-- LSP keymaps on attach
vim.api.nvim_create_autocmd("LspAttach", {
  group = vim.api.nvim_create_augroup("LspKeymaps", {}),
  callback = function(ev)
    local buf = ev.buf
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, { buffer = buf, desc = "Go to definition" })
    vim.keymap.set("n", "gD", vim.lsp.buf.declaration, { buffer = buf, desc = "Go to declaration" })
    vim.keymap.set("n", "gr", vim.lsp.buf.references, { buffer = buf, desc = "References" })
    vim.keymap.set("n", "gI", vim.lsp.buf.implementation, { buffer = buf, desc = "Implementation" })
    vim.keymap.set("n", "gy", vim.lsp.buf.type_definition, { buffer = buf, desc = "Type definition" })
    vim.keymap.set("n", "K", vim.lsp.buf.hover, { buffer = buf, desc = "Hover" })
    vim.keymap.set("n", "<leader>cr", vim.lsp.buf.rename, { buffer = buf, desc = "Rename" })
    vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, { buffer = buf, desc = "Code action" })
    vim.keymap.set("n", "<leader>cd", vim.diagnostic.open_float, { buffer = buf, desc = "Line diagnostics" })
    vim.keymap.set({ "n", "i" }, "<C-S-k>", vim.lsp.buf.signature_help, { buffer = buf, desc = "Signature help" })
    vim.keymap.set("n", "<leader>cs", vim.lsp.buf.document_symbol, { buffer = buf, desc = "Document symbols" })
    vim.keymap.set("n", "<leader>cS", vim.lsp.buf.workspace_symbol, { buffer = buf, desc = "Workspace symbols" })
    vim.keymap.set("n", "<leader>ci", vim.lsp.buf.incoming_calls, { buffer = buf, desc = "Incoming calls" })
    vim.keymap.set("n", "<leader>co", vim.lsp.buf.outgoing_calls, { buffer = buf, desc = "Outgoing calls" })
  end,
})
