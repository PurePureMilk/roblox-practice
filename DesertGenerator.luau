-- Desert Map reconstruction from the supplied Roblox course screenshots.
--
-- INSTALL
-- 1. Open a new place or a copy of your place. Stay in Edit Mode (press Stop if testing).
--    For a fresh Baseplate template, remove its Baseplate and SpawnLocation before building,
--    or use an Offset that moves the generator clear of existing objects.
-- 2. In Explorer, insert a ModuleScript under ServerStorage and name it DesertGenerator.
--    Open it, select all of the starter code, and paste this entire file.
-- 3. Open Window > Script > Command Bar and run this single line:
--    require(game.ServerStorage.DesertGenerator).run({Mode = "preview"})
-- 4. Check Output for the bounds and any blockers. Save a separate .rbxl backup before
--    overwriting existing terrain. To build the map and apply its storm lighting:
--    require(game.ServerStorage.DesertGenerator).run({Mode = "build", ApplyGlobalLook = true})
-- 5. In Explorer, select a Hut or Cactus model and press F to frame it. For a ground-level
--    check, use Play Here from a camera near a pool. Stop the test before saving.
--    Use File > Save to File and save as DesertMap.rbxl.
--
-- OPTIONS (passed in the table, with examples below)
-- Component = "all", "terrain", "huts", "cacti", "dust", "look", or "presentation".
-- Profile = "storm" or "daylight". To switch both lighting and particles, run "look" and
-- "dust" with the same profile, or use Component = "presentation" to run both together.
-- Offset = Vector3.new(0, 0, 0) by default. Each coordinate must be a multiple of 4.
-- Changing a saved terrain offset requires restoring that terrain or using a fresh copy.
-- Seed = 1949 by default. Reuse it when regenerating the same terrain or cactus placements.
-- ApplyGlobalLook = true applies place-wide lighting and water settings. It also allows
-- adjustments to existing Atmosphere and Clouds objects, if present. Other effects are kept.
-- AllowTerrainOverwrite = true permits a terrain write over nonempty or manually edited
-- voxels, within the printed box only. Save a separate .rbxl first. Existing Parts that
-- intersect the terrain box still block the terrain write.
-- Skybox = optional table of six verified Roblox image IDs, keyed SkyboxBk, SkyboxDn,
-- SkyboxFt, SkyboxLf, SkyboxRt, SkyboxUp. Supply it only with the storm look. In its
-- absence Studio uses the existing sky and approximate dynamic clouds.
--
-- Rebuild only cacti:
-- require(game.ServerStorage.DesertGenerator).run({Mode="build", Component="cacti"})
-- Review terrain in daylight without rebuilding it:
-- require(game.ServerStorage.DesertGenerator).run({Mode="build", Component="presentation", Profile="daylight", ApplyGlobalLook=true})
-- Restore the most recent terrain snapshot in the current Studio/module session:
-- require(game.ServerStorage.DesertGenerator).run({Mode="restoreTerrain"})
-- For durable recovery after reopening Studio, open your saved backup .rbxl.
-- Terrain restoration changes voxels only. Any generated props are still editable in
-- Workspace > Generated Desert. A terrain rerun can change ground height. Rerun huts
-- and cacti separately when you want to resnap them to the ground.
--
-- The ModuleScript is only run by the Command Bar in Edit Mode. Keeping it in
-- ServerStorage is optional once you're done making changes.

local Workspace = game:GetService("Workspace")
local Lighting = game:GetService("Lighting")
local RunService = game:GetService("RunService")
local Terrain = Workspace.Terrain

local Generator = {}
local OWNER_ATTRIBUTE = "DesertGeneratorOwner"
local OWNER = "CourseDesert"
local ROOT_NAME = "Generated Desert"
local MANIFEST_NAME = "Terrain Record"
local GRID = 4
local CHUNK = 128
local MIN = Vector3.new(-512, -64, -448)
local MAX = Vector3.new(512, 112, 448)
local CHANNELS = {"SolidMaterial", "SolidOccupancy", "LiquidOccupancy"}

local AIR = Enum.Material.Air
local SAND = Enum.Material.Sand
local SANDSTONE = Enum.Material.Sandstone
local materialsByValue = {}
for _, material in ipairs(Enum.Material:GetEnumItems()) do
    materialsByValue[material.Value] = material
end

local function rgb(r, g, b)
    return Color3.fromRGB(r, g, b)
end

local function owned(object)
    return object:GetAttribute(OWNER_ATTRIBUTE) == OWNER
end

local function create(className, name, parent)
    local object = Instance.new(className)
    object.Name = name
    object:SetAttribute(OWNER_ATTRIBUTE, OWNER)
    object.Parent = parent
    return object
end

local function managedChild(parent, name, className)
    local child = parent:FindFirstChild(name)
    if child then
        assert(owned(child) and child:IsA(className), "Name is already in use: " .. child:GetFullName())
    end
    return child
end

local function safeToReplace(folder)
    if folder then
        for _, child in ipairs(folder:GetDescendants()) do
            assert(owned(child), "Move this unrelated instance out of the generated folder first: " .. child:GetFullName())
        end
    end
end

local function replaceFolder(parent, name, build)
    local old = managedChild(parent, name, "Folder")
    safeToReplace(old)
    local nextFolder = create("Folder", name)
    local ok, message = pcall(build, nextFolder)
    if not ok then
        nextFolder:Destroy()
        error(message, 0)
    end
    nextFolder.Parent = parent
    if old then
        old:Destroy()
    end
end

-- Heights and outlines are estimates. X/Z are local map coordinates.
-- Hills are ordered {center X, center Z, radius X, radius Z, rise, angle}.
local HILLS = {
    {-330, -245, 165, 245, 42, -14},
    {35, -125, 90, 195, 26, -34}, -- Sandy ridge between the two main basins
    {-305, 85, 155, 150, 33, 26},
    {-25, 310, 290, 135, 48, -8},
    {255, 302, 180, 145, 32, 16},
    {395, -105, 130, 235, 29, -15},
    {-210, -350, 180, 100, 14, 0},
}

-- Each basin has a level, a depth, and overlapping lobes defining its shoreline.
local BASINS = {
    {level = 20, depth = 13, lobes = {
        {-90, -220, 102, 77, -13},
        {-130, -245, 63, 53, 10},
    }},
    {level = 22, depth = 17, lobes = {
        {-55, -46, 88, 56, 22},
        {-119, -8, 82, 42, -15},
        {-181, 35, 79, 34, -34},
    }},
    {level = 22, depth = 10, lobes = {
        {-185, 220, 74, 30, -23},
        {-222, 243, 41, 25, -9},
    }},
}

local HUTS = {
    {x = 132.55, z = 76.45, facing = -13},
    {x = 219.45, z = 91.55, facing = 4},
}
local CACTI = {
    {-322, -308}, {-230, -119}, {-209, 6}, {-347, 75},
    {-363, 220}, {-125, 179}, {-37, 262}, {80, 323},
    {115, 129}, {242, 28}, {278, 193}, {389, -33}, {359, 315},
}

local function smoothstep(value)
    local t = math.clamp(value, 0, 1)
    return t * t * (3 - 2 * t)
end

local function ellipse(x, z, spec)
    local angle = math.rad(spec[6] or spec[5])
    local c, s = math.cos(angle), math.sin(angle)
    local dx, dz = x - spec[1], z - spec[2]
    local u = (c * dx + s * dz) / spec[3]
    local v = (-s * dx + c * dz) / spec[4]
    return math.sqrt(u * u + v * v)
end

local function surfaceAt(x, z, seed)
    local broad = math.noise(x / 168, z / 168, seed * 0.013)
    local fine = math.noise(x / 48, z / 48, seed * 0.023)
    local height = 29 + broad * 11 + fine * 3
    for _, hill in ipairs(HILLS) do
        local distance = ellipse(x, z, hill)
        height = height + hill[5] * math.exp(-2.6 * distance * distance)
    end

    -- Keep the hut thresholds on open, walkable sand without making flat square pads.
    for _, hut in ipairs(HUTS) do
        local distance = math.sqrt((x - hut.x) ^ 2 + (z - hut.z) ^ 2)
        local blend = smoothstep((65 - distance) / 43)
        height = height + (32 - height) * blend
    end

    local waterLevel
    for _, basin in ipairs(BASINS) do
        local radius = math.huge
        for _, lobe in ipairs(basin.lobes) do
            local distance = ellipse(x, z, lobe)
            if radius == math.huge then
                radius = distance
            else
                local smoothJoin = math.max(0.22 - math.abs(radius - distance), 0)
                radius = math.min(radius, distance) - smoothJoin ^ 2 / 0.88
            end
        end
        radius = radius + math.noise(x / 63, z / 63, seed * 0.041) * 0.11
        if radius < 1 then
            height = basin.level - basin.depth * smoothstep((1 - radius) / 0.61)
            waterLevel = basin.level
        elseif radius < 1.4 then
            height = basin.level + (height - basin.level) * smoothstep((radius - 1) / 0.4)
        end
    end
    return height, waterLevel, 12 + broad * 7 + fine * 3
end

local function makeChunks(offset)
    local chunks = {}
    for x = MIN.X, MAX.X - GRID, CHUNK do
        for z = MIN.Z, MAX.Z - GRID, CHUNK do
            local low = Vector3.new(x, MIN.Y, z)
            local high = Vector3.new(math.min(x + CHUNK, MAX.X), MAX.Y, math.min(z + CHUNK, MAX.Z))
            table.insert(chunks, {
                key = ("Chunk_%02d"):format(#chunks + 1),
                low = low,
                size = (high - low) / GRID,
                region = Region3.new(low + offset, high + offset),
            })
        end
    end
    return chunks
end

local function makeChannels(chunk, cell)
    local materials, solids, liquids = {}, {}, {}
    for x = 1, chunk.size.X do
        materials[x], solids[x], liquids[x] = {}, {}, {}
        for y = 1, chunk.size.Y do
            local materialRow, solidRow, liquidRow = {}, {}, {}
            for z = 1, chunk.size.Z do
                materialRow[z], solidRow[z], liquidRow[z] = cell(x, y, z)
            end
            materials[x][y], solids[x][y], liquids[x][y] = materialRow, solidRow, liquidRow
        end
    end
    return {SolidMaterial = materials, SolidOccupancy = solids, LiquidOccupancy = liquids}
end

local function generatedChannels(chunk, seed)
    local columns = {}
    for x = 1, chunk.size.X do
        columns[x] = {}
        for z = 1, chunk.size.Z do
            local localX = chunk.low.X + (x - 0.5) * GRID
            local localZ = chunk.low.Z + (z - 0.5) * GRID
            local height, water, cap = surfaceAt(localX, localZ, seed)
            columns[x][z] = {height = height, water = water, cap = cap}
        end
    end
    return makeChannels(chunk, function(x, y, z)
        local bottom = chunk.low.Y + (y - 1) * GRID
        local column = columns[x][z]
        local solid = math.clamp((column.height - bottom) / GRID, 0, 1)
        local liquid = 0
        if column.water then
            liquid = math.clamp((column.water - bottom) / GRID, 0, 1) - solid
            liquid = math.max(liquid, 0)
        end
        local material = AIR
        if solid > 0 then
            material = bottom + GRID / 2 < column.height - column.cap and SANDSTONE or SAND
        end
        return material, solid, liquid
    end)
end

-- Store the exact engine readback as packed material and 32-bit occupancy values.
-- Two rolling checksums detect edits to the generated region across Studio sessions.
local CELL_BYTES = 10
local function captureChunk(chunk)
    local data = Terrain:ReadVoxelChannels(chunk.region, GRID, CHANNELS)
    local packed = buffer.create(chunk.size.X * chunk.size.Y * chunk.size.Z * CELL_BYTES)
    local index, occupied, hashA, hashB = 0, 0, 17, 31
    for x = 1, chunk.size.X do
        for y = 1, chunk.size.Y do
            local mats = data.SolidMaterial[x][y]
            local solids = data.SolidOccupancy[x][y]
            local liquids = data.LiquidOccupancy[x][y]
            for z = 1, chunk.size.Z do
                local material, solid, liquid = mats[z].Value, solids[z], liquids[z]
                if solid > 0 or liquid > 0 then
                    occupied = occupied + 1
                end
                buffer.writeu16(packed, index, material)
                buffer.writef32(packed, index + 2, solid)
                buffer.writef32(packed, index + 6, liquid)
                local solidBits = buffer.readu32(packed, index + 2)
                local liquidBits = buffer.readu32(packed, index + 6)
                hashA = (hashA * 65599 + material + solidBits * 3 + liquidBits * 7) % 2147483647
                hashB = (hashB * 8191 + material * 17 + solidBits * 7 + liquidBits * 3) % 2147483629
                index = index + CELL_BYTES
            end
        end
    end
    return {packed = packed, occupied = occupied, signature = ("%d:%d"):format(hashA, hashB)}
end

local function writeSnapshot(chunk, snapshot)
    local index = 0
    local packed = snapshot.packed
    local data = makeChannels(chunk, function()
        local material = materialsByValue[buffer.readu16(packed, index)]
        local solid = buffer.readf32(packed, index + 2)
        local liquid = buffer.readf32(packed, index + 6)
        index = index + CELL_BYTES
        return material, solid, liquid
    end)
    Terrain:WriteVoxelChannels(chunk.region, GRID, data)
end

local function intersectingParts(root, offset)
    local low, high = MIN + offset, MAX + offset
    local matches = {}
    for _, part in ipairs(Workspace:GetDescendants()) do
        if part:IsA("BasePart") and part ~= Terrain
            and not (root and part:IsDescendantOf(root) and owned(part)) then
            local frame = part.CFrame
            local half = part.Size / 2
            local right, up, back = frame.RightVector, frame.UpVector, frame.LookVector
            local extent = Vector3.new(
                math.abs(right.X) * half.X + math.abs(up.X) * half.Y + math.abs(back.X) * half.Z,
                math.abs(right.Y) * half.X + math.abs(up.Y) * half.Y + math.abs(back.Y) * half.Z,
                math.abs(right.Z) * half.X + math.abs(up.Z) * half.Y + math.abs(back.Z) * half.Z
            )
            local bottom, top = part.Position - extent, part.Position + extent
            if bottom.X < high.X and top.X > low.X and bottom.Y < high.Y and top.Y > low.Y
                and bottom.Z < high.Z and top.Z > low.Z then
                table.insert(matches, part:GetFullName())
            end
        end
    end
    return matches
end

local function terrainPreflight(chunks, manifest, root, options, saveSnapshot)
    print(("[Desert] Voxel bounds: (%s) through (%s), upper bounds exclusive."):format(
        tostring(MIN + options.Offset), tostring(MAX + options.Offset)
    ))
    local overlaps = intersectingParts(root, options.Offset)
    for index = 1, math.min(#overlaps, 6) do
        warn("[Desert] Overlapping Part: " .. overlaps[index])
    end
    local snapshot, occupied, edited = {}, 0, 0
    for index, chunk in ipairs(chunks) do
        local capture = captureChunk(chunk)
        occupied = occupied + capture.occupied
        if manifest and manifest:GetAttribute(chunk.key) ~= capture.signature then
            edited = edited + 1
        end
        if saveSnapshot then
            snapshot[index] = capture
        end
        if index % 4 == 0 then
            task.wait()
        end
    end
    print(("[Desert] %d occupied voxels, %d edited chunks, %d overlapping Parts."):format(
        occupied, edited, #overlaps
    ))
    local reason
    if #overlaps > 0 then
        reason = "Terrain box overlaps unrelated Parts. Use a clear area or a separate place."
    elseif not options.AllowTerrainOverwrite and (edited > 0 or (not manifest and occupied > 0)) then
        reason = "Terrain has existing voxels or manual edits. Save a backup and set AllowTerrainOverwrite=true to proceed."
    end
    return snapshot, reason
end

local lastTerrainBackup

local function writeTerrainTransaction(chunks, before, writeChunk)
    local signatures = {}
    local attempted = 0
    local ok, message = pcall(function()
        for index, chunk in ipairs(chunks) do
            assert(captureChunk(chunk).signature == before[index].signature, "Terrain changed during the preflight.")
            attempted = index
            writeChunk(chunk, index)
            signatures[chunk.key] = captureChunk(chunk).signature
        end
    end)
    if not ok then
        local rollbackFailed = false
        for index = attempted, 1, -1 do
            local restored = pcall(writeSnapshot, chunks[index], before[index])
            rollbackFailed = rollbackFailed or not restored
        end
        if rollbackFailed then
            error("A terrain write and rollback failed. Open the pre-build .rbxl backup. " .. tostring(message), 0)
        end
        error("Terrain transaction aborted. " .. tostring(message), 0)
    end
    return signatures
end

local function buildTerrain(root, manifest, chunks, snapshot, options)
    local signatures = writeTerrainTransaction(chunks, snapshot, function(chunk)
        Terrain:WriteVoxelChannels(chunk.region, GRID, generatedChannels(chunk, options.Seed))
    end)
    lastTerrainBackup = {
        snapshots = snapshot,
        offset = options.Offset,
        hadManifest = manifest ~= nil,
        previousAttributes = manifest and manifest:GetAttributes(),
    }
    local record = manifest or create("Folder", MANIFEST_NAME, root)
    record:SetAttribute("Offset", options.Offset)
    record:SetAttribute("Seed", options.Seed)
    for key, value in pairs(signatures) do
        record:SetAttribute(key, value)
    end
end

local function restoreTerrain(root)
    local backup = lastTerrainBackup
    assert(backup, "No terrain snapshot in this module session. Open your pre-build .rbxl backup.")
    local manifest = root and managedChild(root, MANIFEST_NAME, "Folder")
    assert(manifest and manifest:GetAttribute("Offset") == backup.offset, "Terrain record no longer matches the backup.")
    safeToReplace(manifest)
    print(("[Desert] Restoring voxels within (%s) through (%s), upper bounds exclusive."):format(
        tostring(MIN + backup.offset), tostring(MAX + backup.offset)
    ))
    local chunks = makeChunks(backup.offset)
    local current = {}
    for index, chunk in ipairs(chunks) do
        current[index] = captureChunk(chunk)
        assert(current[index].signature == manifest:GetAttribute(chunk.key),
            "Terrain has been edited since generation. Save a copy before using the original .rbxl backup.")
        if index % 4 == 0 then
            task.wait()
        end
    end
    writeTerrainTransaction(chunks, current, function(chunk, index)
        writeSnapshot(chunk, backup.snapshots[index])
    end)
    if backup.hadManifest then
        for key, value in pairs(backup.previousAttributes) do
            manifest:SetAttribute(key, value)
        end
    else
        manifest:Destroy()
    end
    lastTerrainBackup = nil
    print("[Desert] Restored the pre-write voxels. Existing props were kept.")
end

local function part(className, name, parent, size, frame, color, material, collidable)
    local object = create(className, name)
    object.Size = size
    object.CFrame = frame
    object.Color = color
    object.Material = material
    object.Anchored = true
    object.CanCollide = collidable
    object.CanTouch = false
    object.CanQuery = collidable
    object.Parent = parent
    return object
end

local function block(name, parent, size, frame, color, material, collidable)
    return part("Part", name, parent, size, frame, color, material, collidable)
end

local function rod(name, parent, start, finish, diameter, color, material)
    local direction = (finish - start).Unit
    local reference = math.abs(direction.Y) > 0.95 and Vector3.zAxis or Vector3.yAxis
    local frame = CFrame.fromMatrix((start + finish) / 2, direction, (reference - direction * direction:Dot(reference)).Unit)
    local object = block(name, parent, Vector3.new((finish - start).Magnitude, diameter, diameter),
        frame, color, material, false)
    object.Shape = Enum.PartType.Cylinder
    return object
end

local function roundedJoint(name, parent, point, diameter, color, material)
    local object = block(name, parent, Vector3.one * diameter, CFrame.new(point), color, material, false)
    object.Shape = Enum.PartType.Ball
    return object
end

local function roofTriangle(parent, a, b, c, color)
    -- Make the triangle from two right-angle wedges using its longest side as the base.
    local ab, ac, bc = b - a, c - a, c - b
    if ab:Dot(ab) > ac:Dot(ac) and ab:Dot(ab) > bc:Dot(bc) then
        c, a = a, c
    elseif ac:Dot(ac) > bc:Dot(bc) and ac:Dot(ac) > ab:Dot(ab) then
        a, b = b, a
    end
    ab, ac, bc = b - a, c - a, c - b
    local right = ab:Cross(ac).Unit
    local back = bc.Unit
    local up = bc:Cross(right).Unit
    local height = math.abs(ab:Dot(up))
    local widthB, widthC = math.abs(ab:Dot(back)), math.abs(ac:Dot(back))
    if widthB > 0.05 then
        part("WedgePart", "Roof wedge", parent, Vector3.new(0.2, height, widthB),
            CFrame.fromMatrix((a + b) / 2, right, up, back), color, Enum.Material.WoodPlanks, true)
    end
    if widthC > 0.05 then
        part("WedgePart", "Roof wedge", parent, Vector3.new(0.2, height, widthC),
            CFrame.fromMatrix((a + c) / 2, -right, up, -back), color, Enum.Material.WoodPlanks, true)
    end
end

local function groundAt(x, z, offset)
    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Include
    params.FilterDescendantsInstances = {Terrain}
    local origin = offset + Vector3.new(x, MAX.Y + 2, z)
    local hit = Workspace:Raycast(origin, Vector3.new(0, MIN.Y - MAX.Y - 4, 0), params)
    assert(hit and hit.Material ~= Enum.Material.Water,
        ("Expected dry terrain at local X/Z %.2f, %.2f."):format(x, z))
    return hit.Position
end

local function buildHuts(parent, offset)
    local panelCount = 24
    local radius, wallHeight, roofRadius, roofRise = 18.4, 9, 21, 11.6
    local wallColor = rgb(107, 96, 73)
    local roofColors = {rgb(217, 211, 183), rgb(212, 206, 179), rgb(221, 215, 190)}
    local detailColor = rgb(182, 173, 145)

    for index, hut in ipairs(HUTS) do
        local base = groundAt(hut.x, hut.z, offset) - Vector3.yAxis * 0.38
        local model = create("Model", ("Hut %02d"):format(index), parent)
        local facing = math.rad(hut.facing)
        local function point(angle, distance, height)
            return base + Vector3.new(math.sin(angle) * distance, height, -math.cos(angle) * distance)
        end
        local function panelFrame(angle, y)
            local center = point(angle, radius, y)
            return CFrame.lookAt(center, center + Vector3.new(math.sin(angle), 0, -math.cos(angle)))
        end

        local panelWidth = 2 * radius * math.tan(math.pi / panelCount) + 0.12
        for panelIndex = 0, panelCount - 1 do
            local angle = facing + (panelIndex + 0.5) * 2 * math.pi / panelCount
            local doorway = panelIndex == 0 or panelIndex == panelCount - 1
            local height = doorway and 1.3 or wallHeight
            block(doorway and "Door header" or "Round wall panel", model, Vector3.new(panelWidth, height, 1.05),
                panelFrame(angle, wallHeight - height / 2), wallColor, Enum.Material.Sandstone, true)
        end

        local roof = create("Model", "Pale radial roof", model)
        local roofPanels = 16
        local peak = base + Vector3.yAxis * (wallHeight + roofRise)
        for sector = 0, roofPanels - 1 do
            local angleA = facing + 2 * math.pi * sector / roofPanels
            local angleB = facing + 2 * math.pi * (sector + 1) / roofPanels
            local eaveA = point(angleA, roofRadius, wallHeight)
            local eaveB = point(angleB, roofRadius, wallHeight)
            roofTriangle(roof, peak, eaveA, eaveB, roofColors[sector % #roofColors + 1])
            local lift = Vector3.yAxis * 0.18
            rod("Radial seam", roof, eaveA + lift, peak + lift, 0.16, detailColor, Enum.Material.Wood)
            rod("Eave edge", roof, eaveA, eaveB, 0.38, roofColors[1], Enum.Material.Wood)
        end
        model.WorldPivot = CFrame.new(base) * CFrame.Angles(0, -facing, 0)
    end
end

local function buildCacti(parent, offset, seed)
    local random = Random.new(seed)
    local green, ribColor = rgb(83, 100, 61), rgb(103, 117, 72)
    local material = Enum.Material.SmoothPlastic
    for index, anchor in ipairs(CACTI) do
        local base = groundAt(anchor[1], anchor[2], offset) - Vector3.yAxis * 0.45
        local pivot = CFrame.new(base) * CFrame.Angles(0, random:NextNumber(0, 2 * math.pi), 0)
        local scale = random:NextNumber(0.76, 1.17)
        local model = create("Model", ("Cactus %02d"):format(index), parent)
        model.WorldPivot = pivot

        local trunkHeight = 16.7
        local function world(x, y, z)
            return pivot:PointToWorldSpace(Vector3.new(x, y, z) * scale)
        end
        local tip = world(0, trunkHeight, 0)
        rod("Main stem", model, base, tip, 1.48 * scale, green, material)
        roundedJoint("Rounded stem tip", model, tip, 1.48 * scale, green, material)
        for rib = 0, 7 do
            local angle = rib * math.pi / 4
            local x, z = math.cos(angle) * 0.7, math.sin(angle) * 0.7
            rod("Stem rib", model, world(x, 0.35, z), world(x, trunkHeight - 0.2, z),
                0.13 * scale, ribColor, material)
        end

        local function arm(side, y, tipHeight)
            local points = {
                world(0.38 * side, y, 0),
                world(1.62 * side, y + 0.18, 0),
                world(2.72 * side, y + 0.9, 0),
                world(3.05 * side, y + 2.1, 0),
                world(3.10 * side, tipHeight, 0),
            }
            local diameter = 0.9 * scale
            for segment = 1, #points - 1 do
                rod("Arm segment", model, points[segment], points[segment + 1], diameter, green, material)
                roundedJoint("Rounded arm joint", model, points[segment + 1], diameter, green, material)
            end
        end
        arm(-1, 4.9, random:NextNumber(12.1, 14.6))
        arm(1, 4.4, random:NextNumber(8.1, 10.1))
    end
end

local function buildDust(parent, options)
    -- Large invisible source boxes emit a sparse layer of grains across the walking area.
    -- Distance haze comes from Lighting, so the dust can stay light and inexpensive.
    if options.Profile == "daylight" then
        return
    end
    local zones = {
        {232, 45, -288}, {232, 45, -96}, {232, 49, 96}, {232, 53, 288},
    }
    for index, zone in ipairs(zones) do
        local anchor = block(("Sand Effect Volume %02d"):format(index), parent, Vector3.new(660, 58, 190),
            CFrame.new(options.Offset + Vector3.new(zone[1], zone[2], zone[3])),
            rgb(249, 226, 170), Enum.Material.SmoothPlastic, false)
        anchor.Transparency = 1
        anchor.CastShadow = false
        local emitter = create("ParticleEmitter", "Windblown sand", anchor)
        emitter.Texture = "rbxasset://textures/particles/sparkles_main.dds"
        emitter.Shape = Enum.ParticleEmitterShape.Box
        emitter.ShapeInOut = Enum.ParticleEmitterShapeInOut.Outward
        emitter.ShapeStyle = Enum.ParticleEmitterShapeStyle.Volume
        emitter.EmissionDirection = Enum.NormalId.Left
        emitter.Orientation = Enum.ParticleOrientation.FacingCamera
        emitter.SpreadAngle = Vector2.zero
        emitter.Speed = NumberRange.new(85, 100)
        emitter.Lifetime = NumberRange.new(3, 4.8)
        emitter.Rate = 24
        emitter.LightInfluence = 1
        emitter.LightEmission = 0
        emitter.Color = ColorSequence.new(rgb(249, 226, 170))
        emitter.Size = NumberSequence.new(0.75, 0.35)
        emitter.Transparency = NumberSequence.new({
            NumberSequenceKeypoint.new(0, 1),
            NumberSequenceKeypoint.new(0.12, 0.27),
            NumberSequenceKeypoint.new(0.68, 0.43),
            NumberSequenceKeypoint.new(1, 1),
        })
    end
end

local SKY_FACES = {"SkyboxBk", "SkyboxDn", "SkyboxFt", "SkyboxLf", "SkyboxRt", "SkyboxUp"}

local function sharedEffect(parent, className, name)
    local current = parent:FindFirstChildOfClass(className)
    return current or create(className, name, parent)
end

local function setEffect(parent, className, name, properties)
    local effect = managedChild(parent, name, className) or create(className, name, parent)
    for property, value in pairs(properties) do
        effect[property] = value
    end
end

local function setSkybox(faces)
    local sky = Lighting:FindFirstChildOfClass("Sky")
    if faces then
        sky = sky or create("Sky", "Desert Sky", Lighting)
        for _, face in ipairs(SKY_FACES) do
            local originalKey = "DesertOriginal_" .. face
            if sky:GetAttribute(originalKey) == nil then
                sky:SetAttribute(originalKey, sky[face])
            end
            local value = faces[face]
            sky[face] = value:match("^%d+$") and "rbxassetid://" .. value or value
        end
    elseif sky then
        for _, face in ipairs(SKY_FACES) do
            local originalKey = "DesertOriginal_" .. face
            local original = sky:GetAttribute(originalKey)
            if original ~= nil then
                sky[face] = original
                sky:SetAttribute(originalKey, nil)
            end
        end
    end
end

local function buildLook(options)
    local storm = options.Profile == "storm"
    local atmosphere = sharedEffect(Lighting, "Atmosphere", "Desert Atmosphere")
    local clouds = sharedEffect(Terrain, "Clouds", "Desert Clouds")
    atmosphere.Color = storm and rgb(230, 202, 124) or rgb(199, 220, 235)
    atmosphere.Decay = storm and rgb(128, 104, 56) or rgb(151, 174, 197)
    atmosphere.Density = storm and 0.43 or 0.20
    atmosphere.Offset = storm and 0.16 or 0.17
    atmosphere.Haze = storm and 3.4 or 0.35
    atmosphere.Glare = 0

    clouds.Enabled = true
    clouds.Cover = storm and 0.69 or 0.21
    clouds.Density = storm and 0.67 or 0.30
    clouds.Color = storm and rgb(151, 130, 88) or rgb(235, 238, 245)
    Terrain.WaterColor = rgb(49, 127, 160)
    Terrain.WaterTransparency = 0.38
    Terrain.WaterReflectance = 0.17

    Lighting.ClockTime = 14.3
    Lighting.Brightness = storm and 1.8 or 2.1
    Lighting.OutdoorAmbient = storm and rgb(133, 120, 90) or rgb(144, 148, 151)
    setEffect(Lighting, "ColorCorrectionEffect", "Desert Color Correction", {
        Enabled = storm,
        TintColor = rgb(249, 226, 152),
        Saturation = -0.12,
        Contrast = 0.035,
        Brightness = -0.025,
    })
    setEffect(Lighting, "BlurEffect", "Desert Blur", {Enabled = storm, Size = 2})

    setSkybox(options.Skybox)
    print("[Desert] Applied place-wide " .. options.Profile .. " lighting and water settings.")
end

local function optionsFor(input, manifest)
    input = input or {}
    local defaults = {
        Mode = "preview",
        Component = "all",
        Profile = "storm",
        Offset = manifest and manifest:GetAttribute("Offset") or Vector3.zero,
        Seed = manifest and manifest:GetAttribute("Seed") or 1949,
        AllowTerrainOverwrite = false,
        ApplyGlobalLook = false,
    }
    for key, value in pairs(input) do
        assert(defaults[key] ~= nil or key == "Skybox", "Unknown option: " .. tostring(key))
        defaults[key] = value
    end
    local options = defaults
    local offset = options.Offset
    assert(options.Mode == "preview" or options.Mode == "build" or options.Mode == "restoreTerrain",
        "Mode must be preview, build, or restoreTerrain.")
    assert(options.Profile == "daylight" or options.Profile == "storm", "Unknown Profile.")
    assert(typeof(offset) == "Vector3" and offset.X % GRID == 0 and offset.Y % GRID == 0 and offset.Z % GRID == 0,
        "Offset must be a Vector3 aligned to the 4-stud terrain grid.")
    assert(type(options.Seed) == "number" and options.Seed % 1 == 0 and math.abs(options.Seed) <= 2147483647,
        "Seed must be a signed 32-bit integer.")
    assert(type(options.AllowTerrainOverwrite) == "boolean" and type(options.ApplyGlobalLook) == "boolean",
        "Terrain and lighting switches must be boolean.")
    if options.Skybox ~= nil then
        assert(options.Profile == "storm" and type(options.Skybox) == "table", "Provide Skybox only for storm.")
        for _, face in ipairs(SKY_FACES) do
            local value = options.Skybox[face]
            assert(type(value) == "string" and (value:match("^%d+$") or value:match("^rbxassetid://%d+$")),
                "Supply a verified Roblox image ID for " .. face .. ".")
        end
    end
    return options
end

local COMPONENTS = {
    all = {terrain = true, huts = true, cacti = true, dust = true, look = true},
    terrain = {terrain = true},
    huts = {huts = true},
    cacti = {cacti = true},
    dust = {dust = true},
    look = {look = true},
    presentation = {look = true, dust = true},
}

local function run(input)
    local root = managedChild(Workspace, ROOT_NAME, "Folder")
    local manifest = root and managedChild(root, MANIFEST_NAME, "Folder")
    local options = optionsFor(input, manifest)
    if options.Mode == "restoreTerrain" then
        restoreTerrain(root)
        return true
    end

    local selected = COMPONENTS[options.Component]
    assert(selected, "Unknown component: " .. tostring(options.Component))
    local applyLook = selected.look and options.ApplyGlobalLook
    if selected.look and not applyLook then
        assert(options.Component == "all" or options.Mode == "preview",
            "Lighting is place-wide. Set ApplyGlobalLook=true to apply it.")
        print("[Desert] Place-wide lighting was skipped. Add ApplyGlobalLook=true to apply it.")
    end
    if applyLook then
        managedChild(Lighting, "Desert Color Correction", "ColorCorrectionEffect")
        managedChild(Lighting, "Desert Blur", "BlurEffect")
    end
    if manifest then
        assert(options.Offset == manifest:GetAttribute("Offset"),
            "Offset differs from the saved terrain bounds. Restore terrain or use another place for a new offset.")
    end
    if (selected.huts or selected.cacti) and not selected.terrain and not manifest then
        error("Build terrain first so props can be grounded on it.", 0)
    end
    if root then
        safeToReplace(selected.huts and managedChild(root, "Huts", "Folder"))
        safeToReplace(selected.cacti and managedChild(root, "Cacti", "Folder"))
        safeToReplace(selected.dust and managedChild(root, "Dust", "Folder"))
    end

    local chunks, snapshot
    if selected.terrain then
        chunks = makeChunks(options.Offset)
        local reason
        snapshot, reason = terrainPreflight(chunks, manifest, root, options, options.Mode == "build")
        if reason and options.Mode == "preview" then
            warn("[Desert] " .. reason)
            return false
        end
        assert(not reason, reason)
    end
    if options.Mode == "preview" then
        print("[Desert] Preview passed. No changes were made.")
        return true
    end

    if selected.terrain or selected.huts or selected.cacti or selected.dust then
        root = root or create("Folder", ROOT_NAME, Workspace)
    end
    if selected.terrain then
        buildTerrain(root, manifest, chunks, snapshot, options)
        print("[Desert] Terrain and water built.")
    end
    if selected.huts then
        replaceFolder(root, "Huts", function(folder)
            buildHuts(folder, options.Offset)
        end)
        print("[Desert] Built " .. #HUTS .. " huts.")
    end
    if selected.cacti then
        replaceFolder(root, "Cacti", function(folder)
            buildCacti(folder, options.Offset, options.Seed)
        end)
        print("[Desert] Built " .. #CACTI .. " cacti.")
    end
    if selected.dust then
        replaceFolder(root, "Dust", function(folder)
            buildDust(folder, options)
        end)
        print("[Desert] Dust configured for " .. options.Profile .. ".")
    end
    if applyLook then
        buildLook(options)
    end
    return true
end

local running = false
function Generator.run(input)
    assert(RunService:IsStudio() and RunService:IsEdit(), "Run this only in Studio Edit Mode.")
    assert(not running, "A desert generation command is already running.")
    running = true
    local ok, result = pcall(run, input)
    running = false
    if not ok then
        error("[Desert] " .. tostring(result), 2)
    end
    return result
end

return Generator
