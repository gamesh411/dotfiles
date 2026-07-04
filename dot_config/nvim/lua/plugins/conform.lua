local conform = require("conform")

conform.setup({
  formatters_by_ft = {
    c = { "clang-format" },
    cpp = { "clang-format" },
    python = { "darker" },
    lua = { "stylua" },
  },
})

-- Get git-dirty line ranges for current buffer
local function get_dirty_ranges()
  local file = vim.fn.expand("%:p")
  local result = vim.fn.systemlist({
    "git", "diff", "--unified=0", "--no-color", "HEAD", "--", file,
  })
  if vim.v.shell_error ~= 0 then
    return nil
  end
  local ranges = {}
  for _, line in ipairs(result) do
    -- Match @@ -a,b +c,d @@ patterns
    local start, count = line:match("^@@ %-%d+,?%d* %+(%d+),?(%d*) @@")
    if start then
      start = tonumber(start)
      count = tonumber(count) or 1
      if count > 0 then
        table.insert(ranges, { start = { start, 0 }, ["end"] = { start + count - 1, 999 } })
      end
    end
  end
  return ranges
end

-- Format only git-dirty lines
local function format_dirty()
  local ranges = get_dirty_ranges()
  if not ranges or #ranges == 0 then
    vim.notify("No dirty lines to format", vim.log.levels.INFO)
    return
  end
  for _, range in ipairs(ranges) do
    conform.format({ range = range, lsp_format = "fallback" })
  end
end

vim.keymap.set("n", "<leader>cf", format_dirty, { desc = "Format dirty lines" })
vim.keymap.set("n", "<leader>cF", function()
  conform.format({ lsp_format = "fallback" })
end, { desc = "Format file" })
vim.keymap.set("v", "<leader>cf", function()
  conform.format({ lsp_format = "fallback" })
end, { desc = "Format selection" })
