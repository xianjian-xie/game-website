class TrieNode:

    def __init__(self):
        self.word = False
        self.children = {}


class Trie:
    def __init__(self):
        """
        Initialize your data structure here.
        """
        self.root = TrieNode()
        self.returnlist = []
    def insert(self, word: str) -> None:
        """
        Inserts a word into the trie.
        """
        if word == None:
            return
        node = self.root
        for i in range(len(word)):
            if word[i] not in node.children:
                node.children[word[i]] = TrieNode()
            node = node.children[word[i]]

        node.word = True

    # def search(self, word: str) -> bool:
    #     """
    #     Returns if the word is in the trie.
    #     """
    #     node = self.root
    #     for i in range(len(word)):
    #         if word[i] not in node.children:
    #             return False
    #         node = node.children[word[i]]

    #     return node.word

    def startsWith(self, prefix: str) -> bool:
        """
        Returns if there is any word in the trie that starts with the given prefix.
        """
        node = self.root
        for i in range(len(prefix)):
            if prefix[i] not in node.children:
                return False
            node = node.children[prefix[i]]

        return True


    def getData(self, word: str):
        self.returnlist.clear()
        if self.startsWith(word) is False:
            return None
        else:
            node = self.root
            curlist = []
            for i in range(len(word)):
                node = node.children[word[i]]
                curlist.append(word[i])
            self.backtracking(node, curlist)

        return self.returnlist

    def backtracking(self, node, curlist):
        if node.word:
            self.returnlist.append("".join(curlist))

        if len(node.children) < 1:
            return

        for s in node.children.keys():
            curlist.append(s)
            self.backtracking(node.children[s], curlist)
            curlist.pop()