local leap = require("leap")

-- Core motions
vim.keymap.set({ "n", "x", "o" }, "s", "<Plug>(leap)")
vim.keymap.set("n", "S", "<Plug>(leap-from-window)")

-- Remote operations
vim.keymap.set({ "n", "o" }, "gs", "<Plug>(leap-remote)")
vim.keymap.set({ "n", "o" }, "gS", "<Plug>(leap-remote-linewise)")
vim.keymap.set({ "o" }, "gR", "<Plug>(leap-remote-line)")
vim.keymap.set({ "x", "o" }, "ar", "<Plug>(leap-remote-text-object)")
vim.keymap.set({ "x", "o" }, "ir", "<Plug>(leap-remote-inner-text-object)")

-- Auto-paste after remote yank
vim.api.nvim_create_autocmd("User", {
  pattern = "RemoteOperationDone",
  group = vim.api.nvim_create_augroup("LeapRemote", {}),
  callback = function(event)
    if vim.v.operator == "y" and event.data.register == '"' then
      vim.cmd("normal! p")
    end
  end,
})

-- Treesitter parent node selection
vim.keymap.set({ "x", "o" }, "an", function()
  require("leap.treesitter").select({
    opts = require("leap.user").with_traversal_keys("n", "N"),
  })
end)

-- Preview filter: reduce visual noise
leap.opts.preview = function(ch0, ch1, ch2)
  return not (
    ch1:match("%s")
    or (ch0:match("%a") and ch1:match("%a") and ch2:match("%a"))
  )
end

-- Traversal keys: repeat previous search with <cr>/<bs>
do
  local clever = require("leap.user").with_traversal_keys
  vim.keymap.set({ "n", "x", "o" }, "<cr>", function()
    leap.leap({
      ["repeat"] = true,
      opts = clever("<cr>", "<bs>"),
    })
  end)
  vim.keymap.set({ "n", "x", "o" }, "<bs>", function()
    leap.leap({
      ["repeat"] = true,
      opts = clever("<bs>", "<cr>"),
      backward = true,
    })
  end)
end

-- Remote with native search (off-screen targets)
vim.keymap.set({ "n", "o" }, "g/", function()
  require("leap.remote").action({ jumper = "/" })
end)
vim.keymap.set({ "n", "o" }, "g?", function()
  require("leap.remote").action({ jumper = "?" })
end)

-- Search integration: label visible matches after / or ?
vim.api.nvim_create_autocmd("CmdlineLeave", {
  group = vim.api.nvim_create_augroup("LeapOnSearch", {}),
  callback = function()
    local ev = vim.v.event
    local is_search_cmd = (ev.cmdtype == "/") or (ev.cmdtype == "?")
    vim.schedule(function()
      local cnt = vim.fn.searchcount().total
      if is_search_cmd and (not ev.abort) and (cnt > 1) then
        local labels = leap.opts.safe_labels:gsub("[nN]", "")
        local vim_opts = { ["wo.conceallevel"] = vim.wo.conceallevel }
        leap.leap({
          pattern = vim.fn.getreg("/"),
          windows = { vim.fn.win_getid() },
          opts = { safe_labels = "", labels = labels, vim_opts = vim_opts },
        })
      end
    end)
  end,
})



-- Jump to lines
vim.keymap.set({ "n", "x", "o" }, "|", function()
  local line = vim.fn.line(".")
  local top, bot = math.max(1, line - 3), line + 3
  leap.leap({
    pattern = "\\v(%<" .. top .. "l|%>" .. bot .. "l)$",
    windows = { vim.fn.win_getid() },
    opts = { safe_labels = "" },
  })
end)
