local autocmd = vim.api.nvim_create_autocmd
local augroup = vim.api.nvim_create_augroup

-- autosave toggle
vim.api.nvim_create_user_command("AutoSaveToggle", function()
  local group = augroup("AutoSave", { clear = true })
  if vim.g.autosave_enabled then
    vim.g.autosave_enabled = false
    vim.notify("AutoSave disabled")
  else
    autocmd({ "TextChanged", "TextChangedI" }, {
      group = group,
      pattern = "*",
      callback = function()
        if vim.bo.modified and vim.bo.buftype == "" and vim.fn.expand("%") ~= "" then
          vim.cmd("silent! write")
        end
      end,
    })
    vim.g.autosave_enabled = true
    vim.notify("AutoSave enabled")
  end
end, {})
vim.keymap.set("n", "<leader>as", "<cmd>AutoSaveToggle<cr>", { desc = "Toggle autosave" })

-- highlight on yank
autocmd("TextYankPost", {
  group = augroup("YankHighlight", {}),
  callback = function()
    vim.hl.on_yank()
  end,
})

-- resize splits on window resize
autocmd("VimResized", {
  group = augroup("ResizeSplits", {}),
  callback = function()
    vim.cmd("tabdo wincmd =")
  end,
})

-- go to last cursor position when opening file
autocmd("BufReadPost", {
  group = augroup("LastPosition", {}),
  callback = function(ev)
    local mark = vim.api.nvim_buf_get_mark(ev.buf, '"')
    local lcount = vim.api.nvim_buf_line_count(ev.buf)
    if mark[1] > 0 and mark[1] <= lcount then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})

-- auto-save session on exit (per directory, skip / and $HOME)
autocmd("VimLeavePre", {
  group = augroup("AutoSession", {}),
  callback = function()
    local cwd = vim.fn.getcwd()
    if cwd == "/" or cwd == vim.env.HOME then return end
    local dir = vim.fn.stdpath("data") .. "/sessions"
    vim.fn.mkdir(dir, "p")
    local name = cwd:gsub("/", "_")
    vim.cmd("mksession! " .. vim.fn.fnameescape(dir .. "/" .. name .. ".vim"))
  end,
})
