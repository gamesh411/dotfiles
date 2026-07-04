local telescope = require("telescope")
local builtin = require("telescope.builtin")
local leap = require("leap")

-- Leap integration: pick results with labels
local function get_targets(picker)
  local scroller = require("telescope.pickers.scroller")
  local wininfo = vim.fn.getwininfo(picker.results_win)[1]
  local bottom = wininfo.botline - 2
  local top = math.max(
    scroller.top(
      picker.sorting_strategy,
      picker.max_results,
      picker.manager:num_results()
    ),
    wininfo.topline - 1
  )
  local targets = {}
  for lnum = bottom, top, -1 do
    table.insert(targets, { wininfo = wininfo, pos = { lnum + 1, 1 } })
  end
  return targets
end

local function pick_with_leap(buf)
  local picker = require("telescope.actions.state").get_current_picker(buf)
  leap.leap({
    targets = get_targets(picker),
    action = function(target)
      picker:set_selection(target.pos[1] - 1)
      require("telescope.actions").select_default(buf)
    end,
  })
end

telescope.setup({
  defaults = {
    mappings = {
      i = { ["<a-o>"] = pick_with_leap },
    },
  },
})

telescope.load_extension("undo")

-- Keymaps
local map = vim.keymap.set
map("n", "<leader>ff", builtin.find_files, { desc = "Find files" })
map("n", "<leader>fg", builtin.live_grep, { desc = "Live grep" })
map("n", "<leader>fs", builtin.grep_string, { desc = "Grep word under cursor" })
map("n", "<leader>fb", builtin.buffers, { desc = "Buffers" })
map("n", "<leader>fh", builtin.help_tags, { desc = "Help tags" })
map("n", "<leader>fr", builtin.oldfiles, { desc = "Recent files" })
map("n", "<leader>fd", builtin.diagnostics, { desc = "Diagnostics" })
map("n", "<leader>fu", "<cmd>Telescope undo<cr>", { desc = "Undo tree" })
map("n", "<leader>/", builtin.current_buffer_fuzzy_find, { desc = "Fuzzy find in buffer" })
