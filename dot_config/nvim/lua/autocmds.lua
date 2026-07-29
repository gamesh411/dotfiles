local autocmd = vim.api.nvim_create_autocmd
local augroup = vim.api.nvim_create_augroup

-- highlight on yank (works in both hosts)
autocmd("TextYankPost", {
  group = augroup("YankHighlight", {}),
  callback = function()
    vim.hl.on_yank()
  end,
})

-- Host editor owns layout, sessions and plugin updates when embedded
if vim.g.vscode then
  return
end

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

-- restore <CR> in quickfix/loclist (overridden globally by leap.nvim)
autocmd("FileType", {
  group = augroup("QfEnter", {}),
  pattern = "qf",
  callback = function()
    vim.keymap.set("n", "<CR>", "<CR>", { buffer = true, desc = "Quickfix jump" })
  end,
})

-- Update all plugins (async git pull --ff-only)
vim.api.nvim_create_user_command("PlugUpdate", function()
  local dir = vim.fn.stdpath("data") .. "/site/pack/plugins/opt"
  local names = {}
  for name in vim.fs.dir(dir) do
    table.insert(names, name)
  end
  local total = #names
  local done = 0
  local results = {}

  local function on_all_done()
    vim.schedule(function()
      vim.notify(table.concat(results, "\n"), vim.log.levels.INFO)
      vim.cmd("helptags ALL")
      require("blink.cmp").build():pwait()
      local fzf_dir = dir .. "/telescope-fzf-native.nvim"
      if vim.uv.fs_stat(fzf_dir) then
        vim.fn.system({ "make", "-C", fzf_dir })
      end
      vim.notify("PlugUpdate complete - helptags + blink rebuilt", vim.log.levels.INFO)
    end)
  end

  vim.notify("PlugUpdate: updating " .. total .. " plugins...", vim.log.levels.INFO)
  for _, name in ipairs(names) do
    local path = dir .. "/" .. name
    vim.fn.jobstart({ "git", "-C", path, "pull", "--ff-only" }, {
      stdout_buffered = true,
      on_stdout = function(_, data)
        local out = table.concat(data, "")
        table.insert(results, name .. ": " .. vim.trim(out))
      end,
      on_exit = function()
        done = done + 1
        if done == total then
          on_all_done()
        end
      end,
    })
  end
end, { desc = "Update all plugins (async)" })
