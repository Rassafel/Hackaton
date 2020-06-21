import vk_api


class WallPosts:
    def get_wall_post(self):
        """
        Запрос списка новых постов на стене.
        :return:
        """
        list_posts = list()
        max_id = self.last_id
        for post in self.vk.method(method='wall.get',
                                   values={
                                       'owner_id': self.wall_id,
                                       'count': 5
                                   })['items']:
            post_id = int(post['id'])
            if post_id > self.last_id:
                max_id = max(post_id, max_id)
                list_posts.append(post)
        self.last_id = max_id
        return list_posts

    def get_last_id(self):
        """
        Получение ID последнего поста на стене.
        :return:
        """
        max_id = 0
        for post in self.vk.method(method='wall.get',
                                   values={
                                       'owner_id': self.wall_id,
                                       'count': 2
                                   })['items']:
            max_id = max(int(post['id']), max_id)
        return max_id

    def __init__(self, wall_id: int, vk: vk_api):
        """
        :param wall_id: Ссылка на стену (если группа, то
        значение должно быть со знаком -
        :param vk:
        """
        self.wall_id = wall_id
        self.vk = vk
        self.last_id = self.get_last_id()
