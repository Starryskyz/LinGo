总体目标：为LinGo全栈设计一个英文的html网页前端，要求简约美观。
以flow的形式，flow在左侧，每个tab分别是CGRA HW、Compile、Mapping、Verification、Phycisal Design（留空目前），按顺序来，如果前一个step没有做，后面的step icon将是灰色无法点击，后面的step做了之后，可以回前面的step查看，但如果前面的step重新动作，后面的也变灰需要按顺序重来。
在gui界面的操作缓存应该存入到gui/tmp，尽量不要影响到原有工具目录，对benchmarks、simulation目录的写入被允许。
下面是每个step具体的要求

### CGRA HW
1. 分为左右两侧，左侧渲染一个和gui/hwarch.png长得一致的图，要求是渲染，可以在框内缩小放大，以及选中pe、gib、iob这些东西（都可以用圆形表示，这样方便展示八个方向的连接），选中后会高亮；右侧是对参数的的选择与配置。
2. 默认打开载入的是现有的hardware/src/main/resources/fgra_spec.json
3. 对纯粗粒度阵列来说，在图上显示的PE名称叫C-PE，如果存在lut，那么将PE名称显示为F-PE；GIB有粗细粒度的分别但同一位置合并，只有粗粒度叫C-GIB、有粗细混合叫F/C-GIB，将粗细粒度的连线显示上都接到GIB，不过粗粒度为实线，细粒度为虚线，这个线有多少条，取决于设置的互连线track参数。对于xcore和unified PE，分别显示为XCore、PC-PE。这两种PE应该是不能再叠细粒度lut的？
4. 点击渲染图中的PE，可以调整其类型（C-PE、F-PE、XCore、PC-PE），并且调整其中的算子和LUT（对于C-PE、F-PE），将目前硬件中所有算子放上（最好分下类，形成一个个小类别框），前面加个勾选框钩上代表有，对于C-PE关于LUT的配置（貌似主要是num_input_lut）变灰不可调整，对于XCore、PC-PE算子这部分变灰且不可勾选，PC-PE可以设置LUT，称之为PC-F-PE。提供一个格式刷按键，对某个pe选择完成后，点一下这个格式刷icon，再点一下渲染图中的其他pe，可以将其他pe刷成这个格式；提供一个同构阵列按键，同理点一下可将整个阵列的其他pe全配置成这样
5. 对于右侧配置区，主要分为阵列配置区（在上）和PE配置区（在下），PE的配置在前面已经提到。阵列配置参数如下
row、col
spm bank的大小，显示为填入多少KiB，据此修改`spad_bank_lg_size`  ，例如4KiB为12，界面只显示单个bank大小就可以
spm组相连数fgra_iob_sram_banks_coalesce，默认是列数col，可以调整范围为能整除列数的正整数
粗粒度互连网络每方向的轨道数，`fgra_gib_num_track_cg`  
细粒度互连网络每方向的轨道数，`fgra_gib_num_track_fg`  
这两者应该会影响渲染图上的表示？

如果参数不符合要求，填写框或者选择选项红色高亮

6. 做出修改后，应该缓存，在点击generate spec时统计最终的配置，生成spec并替换。
7. 如果检查到spec文件发生变化，generate RTL按钮应该有状态提示当前RTL过期，点击重新生成（建议是黄色灯），生成成功为绿色和succcess提示，生成失败为红色。命令在hardware/genRTL.sh


### Compile
1. 先选择是用LLVM还是MLIR编译器，前者脚本在benchmarks/compile.sh，后者在benchmarks/mlirCompile.sh，另外执行完要dot2json.sh
2. 选择要编译的程序，每个例子都存放在benchmarks/example/example.c，所以选项是example就可以（要能自动检索benchmarks目录发生的变化例如新增/删除），在左边放一个.c的预览框，要能渲染C/C++语法。除了选择之外，也可以new一个，输入新建的程序name，自动创建benchmarks/name/name.c，此时预览框为空。预览框要能编辑文件和有保存按钮。
3. 选中要编译的程序后，点击右边的compile icon即可编译，对于成功的例子，在刚刚那个预览框右边做一个框渲染一下这个例子的dfg，要求这个渲染可以符合人体直觉的放大缩小，选中node后会高亮node和他的连接边
4. 对于编译结果要有成功和失败的状态提示，和计时，放在compile icon旁边，对于成功编译的例子，给出node数和edge数的展示，这个可以是常驻的，没有编译和编译失败的时候显示为--
5. 编译的log显示在最底下log框，重新点击compile时先clear，再compile和显示log

### Mapping
1. map的操作在mapper/run.sh
2. 选择要map的程序，每个例子编译结果都存放在benchmarks/example/example.json；选择要emit的后端，如all、cocotb、sdk，默认是all
3. 选择完成后，点击右边的map icon即可编译，对于成功的例子，展示映射后的架构渲染图，这个渲染图和HW那里一样，只不过被map的edge像mapped_adg.dot里面一样有颜色方向，粗细粒度和其他单元表示HW一致，被映射的PE显示-----*还没写*
4. 对于编译结果要有成功和失败的状态提示，和计时，放在map icon旁边，对于成功编译的例子，给出II和Latency的展示，这个可以是常驻的，没有map和map失败的时候显示为--

### Verification
先留空

### Phycisal Design
先留空