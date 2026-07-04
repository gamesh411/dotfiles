local _99 = require("99")

local cwd = vim.uv.cwd()
local basename = vim.fs.basename(cwd)
_99.setup({
  provider = _99.Providers.KiroProvider,
  model = "claude-sonnet-4.6",
  logger = {
    level = _99.DEBUG,
    path = "/tmp/" .. basename .. ".99.debug",
    print_on_error = true,
  },
  tmp_dir = "./tmp",
  completion = {
    custom_rules = { "scratch/custom_rules/" },
    files = {},
    source = "blink",
  },
  md_files = { "AGENT.md" },
})

require("which-key").add({
  { "<leader>a", group = "AI-99" },
  {
    mode = "v",
    "<leader>av",
    function()
      _99.visual({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end,
    desc = "99: visual edit selection",
  },
  {
    mode = "n",
    "<leader>ax",
    function() _99.stop_all_requests() end,
    desc = "99: stop all requests",
  },
  {
    mode = "n",
    "<leader>as",
    function()
      _99.search({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end,
    desc = "99: search codebase",
  },
  {
    mode = "n",
    "<leader>ad",
    function()
      _99.vibe({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end,
    desc = "99: vibe",
  },
  {
    mode = "n",
    "<leader>ao",
    function() _99.open() end,
    desc = "99: open",
  },
  {
    mode = "n",
    "<leader>aC",
    function() _99.clear_previous_requests() end,
    desc = "99: clear previous requests",
  },
  {
    mode = "n",
    "<leader>at",
    function()
      _99.tutorial({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end,
    desc = "99: tutorial",
  },
})
